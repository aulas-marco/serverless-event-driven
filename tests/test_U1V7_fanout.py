"""
Testes da Demo U1V7 — Fan-out com SNS + SQS

O que estes testes verificam:
    UMA publicação no tópico SNS entrega mensagens em DUAS filas SQS
    independentes. O produtor não menciona as filas em nenhum momento.

O que NÃO está aqui:
    Criação de filas, assinaturas, ARNs — isso está em TopologiaFanout
    (tests/aws_builder.py). Testes declaram comportamento; builders
    orquestram infraestrutura.
"""
import json
import uuid

import pytest

from tests.aws_builder import TopologiaFanout
from tests.helpers import wait_until
from tests.narracao import narrador


@pytest.fixture(scope="module", autouse=True)
def _demo_banner():
    narrador.demo(
        "U1V7 — Fan-out com SNS + SQS",
        "Uma publicação no tópico entrega em DUAS filas SQS independentes.",
    )


@pytest.fixture(scope="module")
def topologia(sqs, sns) -> TopologiaFanout:
    """Monta a topologia fan-out completa para o módulo de testes."""
    return TopologiaFanout(sqs, sns)


# ── Testes ────────────────────────────────────────────────────────────────────


def test_publicacao_no_topico_retorna_identificador(topologia):
    """
    Smoke test: o tópico existe e aceita publicações.
    O SNS retorna um MessageId único para cada publish.
    """
    message_id = topologia.publicar_pedido("ping")

    assert message_id, "sns.publish deve retornar um MessageId não vazio"


def test_publicacao_entrega_mensagem_na_fila_de_estoque(topologia):
    """
    Uma publicação no SNS deve entregar na fila-estoque.

    Ponto de aprendizado: o produtor faz UMA chamada publish sem mencionar
    a fila. Quem conecta tópico e fila é a assinatura — não o código.
    """
    pedido_id = str(uuid.uuid4())

    topologia.publicar_pedido(pedido_id)

    wait_until(
        lambda: topologia.pedido_chegou_na_fila_estoque(pedido_id),
        timeout=15,
        message="mensagem não chegou em fila-estoque",
    )


def test_publicacao_entrega_mensagem_na_fila_de_notificacao(topologia):
    """
    A mesma publicação também deve chegar em fila-notificacao.
    O SNS entregou para AMBAS as assinaturas — não apenas uma.
    """
    pedido_id = str(uuid.uuid4())

    topologia.publicar_pedido(pedido_id)

    wait_until(
        lambda: topologia.pedido_chegou_na_fila_notificacao(pedido_id),
        timeout=15,
        message="mensagem não chegou em fila-notificacao",
    )


def test_um_publish_entrega_o_mesmo_pedido_nas_duas_filas(topologia):
    """
    Coração do fan-out: 1 publish → MESMO pedidoId nas DUAS filas.

    O produtor faz UMA chamada. O SNS entrega DUAS cópias independentes.
    Se uma consumidora falhar, a outra não é afetada — elas não se conhecem.
    """
    pedido_id = str(uuid.uuid4())

    topologia.publicar_pedido(pedido_id)

    wait_until(
        lambda: topologia.pedido_chegou_nas_duas_filas(pedido_id),
        timeout=15,
        message="pedido não chegou nas duas filas simultaneamente",
    )
    narrador.observacao("Mesmo pedido entregue nas DUAS filas (fan-out)", depois=pedido_id)


def test_raw_delivery_entrega_json_puro_sem_envelope_do_sns(topologia):
    """
    Com RawMessageDelivery=true, o corpo da mensagem é o JSON puro do pedido.

    Sem raw delivery, o SNS envolve o payload num envelope:
        {
            "Type": "Notification",
            "Message": "{\"pedidoId\": \"...\"}"  ← JSON dentro de string
        }
    Isso quebraria o json.loads direto nas consumidoras.
    """
    pedido_id = str(uuid.uuid4())

    topologia.publicar_pedido(pedido_id)

    mensagens = None

    def capturar_mensagem():
        nonlocal mensagens
        mensagens = topologia.receber_da_fila_estoque()
        return any(pedido_id in m["Body"] for m in mensagens)

    wait_until(capturar_mensagem, timeout=15,
               message="mensagem não chegou para validar formato do body")

    corpo = next(m["Body"] for m in mensagens if pedido_id in m["Body"])
    payload = json.loads(corpo)
    narrador.consumo("fila-estoque (JSON puro, sem envelope SNS)", payload)

    assert "pedidoId" in payload, (
        f"O body deve ser JSON puro do pedido, mas chegou: {corpo}"
    )
    assert "Type" not in payload, (
        "O body não deve conter o envelope SNS. "
        "Verifique RawMessageDelivery=true na assinatura."
    )
