"""
Testes da Demo U1V7 — Fan-out com SNS + SQS

Objetivo: verificar que UMA publicação no tópico SNS entrega
mensagens em DUAS filas SQS independentes.

Estes testes validam a INFRAESTRUTURA (topologia), não o código Lambda.
O código das consumidoras (estoque.py, notificacao.py) é trivial;
o que importa é a configuração das assinaturas.

Pré-condição: execute `make setup` antes de rodar estes testes.
"""
import json
import uuid

import pytest

from tests.helpers import wait_until

# ── Fixtures de módulo ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def topic_arn(sns) -> str:
    """Cria (ou reutiliza) o tópico SNS 'pedidos'."""
    resp = sns.create_topic(Name="pedidos")
    return resp["TopicArn"]


@pytest.fixture(scope="module")
def filas(sqs, sns, topic_arn) -> dict:
    """
    Cria as duas filas e as assina no tópico SNS.
    RawMessageDelivery=true: o body da mensagem SQS é o JSON puro,
    sem o envelope SNS com campos Type/MessageId/TopicArn.
    """
    fila_estoque_url = sqs.create_queue(QueueName="fila-estoque")["QueueUrl"]
    fila_notif_url = sqs.create_queue(QueueName="fila-notificacao")["QueueUrl"]

    fila_estoque_arn = sqs.get_queue_attributes(
        QueueUrl=fila_estoque_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]
    fila_notif_arn = sqs.get_queue_attributes(
        QueueUrl=fila_notif_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    # Assinaturas — AQUI mora o fan-out: 1 tópico → 2 filas
    for arn, url in [(fila_estoque_arn, fila_estoque_url), (fila_notif_arn, fila_notif_url)]:
        sns.subscribe(
            TopicArn=topic_arn,
            Protocol="sqs",
            Endpoint=arn,
            Attributes={"RawMessageDelivery": "true"},
        )

    return {
        "estoque_url": fila_estoque_url,
        "notificacao_url": fila_notif_url,
    }


# ── Testes ────────────────────────────────────────────────────────────────────


def test_topico_aceita_publicacao(sns, topic_arn):
    """Smoke test: o tópico existe e aceita uma publicação."""
    resp = sns.publish(TopicArn=topic_arn, Message="ping")
    assert resp["MessageId"], "publish deve retornar um MessageId"


def test_uma_publicacao_chega_na_fila_estoque(sns, sqs, topic_arn, filas):
    """
    UMA publicação no SNS deve entregar na fila-estoque.
    O produtor não sabe que fila-estoque existe — ele só conhece o tópico.
    """
    pedido_id = str(uuid.uuid4())
    sns.publish(TopicArn=topic_arn, Message=json.dumps({"pedidoId": pedido_id}))

    def mensagem_chegou():
        resp = sqs.receive_message(
            QueueUrl=filas["estoque_url"],
            MaxNumberOfMessages=1,
            VisibilityTimeout=5,
        )
        mensagens = resp.get("Messages", [])
        return any(pedido_id in m["Body"] for m in mensagens)

    wait_until(mensagem_chegou, timeout=15, message="mensagem não chegou em fila-estoque")


def test_uma_publicacao_chega_na_fila_notificacao(sns, sqs, topic_arn, filas):
    """
    A MESMA publicação também deve chegar em fila-notificacao.
    Isso demonstra que o SNS entregou para AMBAS as assinaturas.
    """
    pedido_id = str(uuid.uuid4())
    sns.publish(TopicArn=topic_arn, Message=json.dumps({"pedidoId": pedido_id}))

    def mensagem_chegou():
        resp = sqs.receive_message(
            QueueUrl=filas["notificacao_url"],
            MaxNumberOfMessages=1,
            VisibilityTimeout=5,
        )
        mensagens = resp.get("Messages", [])
        return any(pedido_id in m["Body"] for m in mensagens)

    wait_until(mensagem_chegou, timeout=15, message="mensagem não chegou em fila-notificacao")


def test_fanout_o_mesmo_pedido_id_chega_nas_duas_filas(sns, sqs, topic_arn, filas):
    """
    Coração do fan-out: 1 publish → MESMO pedidoId em AMBAS as filas.
    O produtor faz UMA chamada; o SNS entrega DUAS cópias.
    """
    pedido_id = str(uuid.uuid4())
    sns.publish(TopicArn=topic_arn, Message=json.dumps({"pedidoId": pedido_id}))

    def pedido_em_estoque():
        resp = sqs.receive_message(QueueUrl=filas["estoque_url"], MaxNumberOfMessages=10)
        return any(pedido_id in m["Body"] for m in resp.get("Messages", []))

    def pedido_em_notificacao():
        resp = sqs.receive_message(QueueUrl=filas["notificacao_url"], MaxNumberOfMessages=10)
        return any(pedido_id in m["Body"] for m in resp.get("Messages", []))

    wait_until(pedido_em_estoque, timeout=15, message="pedido não chegou em fila-estoque")
    wait_until(pedido_em_notificacao, timeout=15, message="pedido não chegou em fila-notificacao")


def test_body_com_raw_delivery_nao_tem_envelope_sns(sns, sqs, topic_arn, filas):
    """
    Com RawMessageDelivery=true, o body é o JSON puro do pedido.
    Sem raw delivery, o SNS envolveria o payload num envelope com
    campos Type, MessageId, TopicArn, Message — quebrando json.loads direto.
    """
    pedido_id = str(uuid.uuid4())
    sns.publish(TopicArn=topic_arn, Message=json.dumps({"pedidoId": pedido_id}))

    recebido = None

    def capturar():
        nonlocal recebido
        resp = sqs.receive_message(QueueUrl=filas["estoque_url"], MaxNumberOfMessages=1)
        msgs = resp.get("Messages", [])
        for m in msgs:
            if pedido_id in m["Body"]:
                recebido = m["Body"]
                return True
        return False

    wait_until(capturar, timeout=15, message="mensagem não chegou para validar body")

    # Se o body fosse o envelope SNS, json.loads retornaria um dict com "Type", "Message", etc.
    payload = json.loads(recebido)
    assert "pedidoId" in payload, (
        "body deve ser o JSON puro do pedido (RawMessageDelivery=true), "
        f"mas chegou: {recebido}"
    )
    assert "Type" not in payload, "body não deve conter o envelope SNS"
