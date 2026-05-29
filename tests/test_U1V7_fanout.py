"""
Testes da Demo U1V7 — Fan-out com SNS + SQS

O que estes testes verificam:
    UMA publicação no tópico SNS entrega mensagens em DUAS filas SQS
    independentes. O produtor não conhece as filas — apenas o tópico.

O que estes testes NÃO verificam:
    O código das consumidoras (estoque.py, notificacao.py) — ele é
    intencialmente trivial. O que importa aqui é a TOPOLOGIA: como
    a configuração das assinaturas cria o fan-out.

Pré-condição: `make up` (LocalStack rodando).
"""
import json
import uuid

import pytest

from tests.helpers import drain_queue, wait_until

# ── Constantes ────────────────────────────────────────────────────────────────

NOME_DO_TOPICO = "pedidos"
NOME_DA_FILA_ESTOQUE = "fila-estoque"
NOME_DA_FILA_NOTIFICACAO = "fila-notificacao"

# ── Infraestrutura dos testes (fixtures) ──────────────────────────────────────


@pytest.fixture(scope="module")
def topico_pedidos(sns) -> str:
    """Cria (ou reutiliza) o tópico SNS. Retorna o ARN."""
    resposta = sns.create_topic(Name=NOME_DO_TOPICO)
    return resposta["TopicArn"]


@pytest.fixture(scope="module")
def topologia_fanout(sqs, sns, topico_pedidos) -> dict:
    """
    Monta a topologia completa do fan-out:
      1. Cria as duas filas SQS
      2. Assina cada fila no tópico SNS (RawMessageDelivery=true)
      3. Drena mensagens antigas para garantir isolamento entre execuções

    RawMessageDelivery=true: o corpo da mensagem SQS recebida é o JSON
    puro do pedido. Sem isso, o SNS envolve o payload num envelope com
    campos extras (Type, MessageId, TopicArn, Message), quebrando o
    json.loads direto nas consumidoras.
    """
    url_fila_estoque = sqs.create_queue(QueueName=NOME_DA_FILA_ESTOQUE)["QueueUrl"]
    url_fila_notificacao = sqs.create_queue(QueueName=NOME_DA_FILA_NOTIFICACAO)["QueueUrl"]

    arn_fila_estoque = sqs.get_queue_attributes(
        QueueUrl=url_fila_estoque, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    arn_fila_notificacao = sqs.get_queue_attributes(
        QueueUrl=url_fila_notificacao, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    # As duas assinaturas — AQUI mora o fan-out.
    # Uma única publicação no tópico gera entrega em CADA assinante.
    for arn_da_fila in [arn_fila_estoque, arn_fila_notificacao]:
        sns.subscribe(
            TopicArn=topico_pedidos,
            Protocol="sqs",
            Endpoint=arn_da_fila,
            Attributes={"RawMessageDelivery": "true"},
        )

    # Sem drain, mensagens de execuções anteriores ficam na fila e confundem
    # os testes: receive_message pode retornar uma mensagem velha no lugar
    # da nova, causando timeout mesmo que a entrega esteja funcionando.
    drain_queue(sqs, url_fila_estoque)
    drain_queue(sqs, url_fila_notificacao)

    return {
        "url_fila_estoque": url_fila_estoque,
        "url_fila_notificacao": url_fila_notificacao,
    }


# ── Testes ────────────────────────────────────────────────────────────────────


def test_publicacao_no_topico_retorna_identificador(sns, topico_pedidos):
    """
    Verificação básica: o tópico existe e aceita publicações.
    O SNS sempre retorna um MessageId único para cada publish.
    """
    resposta = sns.publish(TopicArn=topico_pedidos, Message="ping")

    assert resposta["MessageId"], "sns.publish deve retornar um MessageId não vazio"


def test_publicacao_entrega_mensagem_na_fila_de_estoque(sns, sqs, topico_pedidos, topologia_fanout):
    """
    Uma publicação no SNS deve entregar na fila-estoque.

    Ponto de aprendizado: o produtor faz UMA chamada publish sem mencionar
    a fila. Quem conecta tópico e fila é a ASSINATURA configurada acima —
    não o código do produtor.
    """
    pedido_id = str(uuid.uuid4())

    sns.publish(TopicArn=topico_pedidos, Message=json.dumps({"pedidoId": pedido_id}))

    def pedido_chegou_na_fila_de_estoque():
        resposta = sqs.receive_message(
            QueueUrl=topologia_fanout["url_fila_estoque"],
            MaxNumberOfMessages=10,
            VisibilityTimeout=5,
        )
        mensagens_recebidas = resposta.get("Messages", [])
        return any(pedido_id in m["Body"] for m in mensagens_recebidas)

    wait_until(
        pedido_chegou_na_fila_de_estoque,
        timeout=15,
        message="mensagem não chegou em fila-estoque",
    )


def test_publicacao_entrega_mensagem_na_fila_de_notificacao(sns, sqs, topico_pedidos, topologia_fanout):
    """
    A mesma publicação também deve chegar em fila-notificacao.
    Demonstra que o SNS entregou para AMBAS as assinaturas — não apenas uma.
    """
    pedido_id = str(uuid.uuid4())

    sns.publish(TopicArn=topico_pedidos, Message=json.dumps({"pedidoId": pedido_id}))

    def pedido_chegou_na_fila_de_notificacao():
        resposta = sqs.receive_message(
            QueueUrl=topologia_fanout["url_fila_notificacao"],
            MaxNumberOfMessages=10,
            VisibilityTimeout=5,
        )
        mensagens_recebidas = resposta.get("Messages", [])
        return any(pedido_id in m["Body"] for m in mensagens_recebidas)

    wait_until(
        pedido_chegou_na_fila_de_notificacao,
        timeout=15,
        message="mensagem não chegou em fila-notificacao",
    )


def test_um_publish_entrega_o_mesmo_pedido_nas_duas_filas(sns, sqs, topico_pedidos, topologia_fanout):
    """
    Coração do fan-out: 1 publish → MESMO pedidoId em AMBAS as filas.

    O produtor faz UMA chamada. O SNS entrega DUAS cópias independentes.
    Se uma consumidora falhar, a outra não é afetada — elas não se conhecem.
    """
    pedido_id = str(uuid.uuid4())

    # Uma única publicação
    sns.publish(TopicArn=topico_pedidos, Message=json.dumps({"pedidoId": pedido_id}))

    def mesmo_pedido_chegou_na_fila_de_estoque():
        resposta = sqs.receive_message(
            QueueUrl=topologia_fanout["url_fila_estoque"],
            MaxNumberOfMessages=10,
        )
        return any(pedido_id in m["Body"] for m in resposta.get("Messages", []))

    def mesmo_pedido_chegou_na_fila_de_notificacao():
        resposta = sqs.receive_message(
            QueueUrl=topologia_fanout["url_fila_notificacao"],
            MaxNumberOfMessages=10,
        )
        return any(pedido_id in m["Body"] for m in resposta.get("Messages", []))

    # O mesmo pedidoId deve aparecer nas duas filas
    wait_until(mesmo_pedido_chegou_na_fila_de_estoque, timeout=15,
               message="pedido não chegou em fila-estoque")
    wait_until(mesmo_pedido_chegou_na_fila_de_notificacao, timeout=15,
               message="pedido não chegou em fila-notificacao")


def test_raw_delivery_entrega_json_puro_sem_envelope_do_sns(sns, sqs, topico_pedidos, topologia_fanout):
    """
    Com RawMessageDelivery=true, o corpo da mensagem SQS é o JSON puro do pedido.

    Sem raw delivery, o SNS envolve o payload num envelope assim:
        {
            "Type": "Notification",
            "MessageId": "...",
            "TopicArn": "...",
            "Message": "{\"pedidoId\": \"...\"}"  ← o JSON real fica aqui, como string
        }
    Isso quebraria o json.loads direto nas consumidoras.
    """
    pedido_id = str(uuid.uuid4())

    sns.publish(TopicArn=topico_pedidos, Message=json.dumps({"pedidoId": pedido_id}))

    corpo_recebido = None

    def encontrar_mensagem_na_fila():
        nonlocal corpo_recebido
        resposta = sqs.receive_message(
            QueueUrl=topologia_fanout["url_fila_estoque"],
            MaxNumberOfMessages=10,
        )
        for mensagem in resposta.get("Messages", []):
            if pedido_id in mensagem["Body"]:
                corpo_recebido = mensagem["Body"]
                return True
        return False

    wait_until(encontrar_mensagem_na_fila, timeout=15,
               message="mensagem não chegou para validar formato do body")

    payload = json.loads(corpo_recebido)

    assert "pedidoId" in payload, (
        "O body deve ser o JSON puro do pedido (RawMessageDelivery=true). "
        f"Recebido: {corpo_recebido}"
    )
    assert "Type" not in payload, (
        "O body não deve conter o envelope SNS (campo 'Type'). "
        "Verifique se RawMessageDelivery=true está ativo na assinatura."
    )
