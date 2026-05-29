"""
Testes da Demo U1V9 — Dead-Letter Queue (DLQ) e Resiliência

O que estes testes verificam:
    Uma poison message (mensagem que sempre falha) é roteada para a DLQ
    após maxReceiveCount tentativas, sem bloquear as mensagens seguintes.

Por que são lentos (~90s por cenário):
    Cada teste aguarda 3 tentativas × 10s de visibility timeout.
    Isso é intencional — o SQS do LocalStack executa o ciclo de retry real.

O que NÃO está aqui:
    Criação de filas, política de reenvio, ESM, deploy da Lambda —
    isso está em FilaComDlq e ConsumidoraDeEstoque (aws_builder.py).
"""
import uuid

import pytest

from tests.aws_builder import ConsumidoraDeEstoque, FilaComDlq
from tests.helpers import assert_never, wait_until

NOME_DA_FILA_PRINCIPAL = "fila-estoque-v9"
NOME_DA_FILA_MORTA = "fila-estoque-v9-dlq"


@pytest.fixture(scope="module")
def fila(sqs) -> FilaComDlq:
    """Cria a fila com DLQ vinculada (maxReceiveCount=3)."""
    return FilaComDlq(sqs, NOME_DA_FILA_PRINCIPAL, NOME_DA_FILA_MORTA)


@pytest.fixture(scope="module")
def consumidora(lam, fila) -> ConsumidoraDeEstoque:
    """Faz o deploy da Lambda e cria o ESM (fila → Lambda)."""
    return ConsumidoraDeEstoque(lam, fila.url_fila_principal)


# ── Testes ────────────────────────────────────────────────────────────────────


@pytest.mark.timeout(120)
def test_mensagem_envenenada_e_roteada_para_dlq_apos_tres_falhas(fila, consumidora):
    """
    Fluxo da poison message:
        Fila → Lambda falha (1ª) → mensagem volta após visibility timeout
        Fila → Lambda falha (2ª) → mensagem volta
        Fila → Lambda falha (3ª) → mensagem volta
        Fila → DLQ (4ª recepção, maxReceiveCount atingido)

    Resultado: a poison message sai do caminho principal.
    A fila fica livre para processar as próximas mensagens.
    """
    sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"

    fila.enviar_mensagem({"sku": sku, "qtd": 1, "defeituoso": True})

    wait_until(
        lambda: fila.mensagem_chegou_na_fila_morta(sku),
        timeout=90,
        interval=2,
        message="a mensagem envenenada não chegou na DLQ no tempo esperado",
    )


@pytest.mark.timeout(120)
def test_dlq_preserva_o_payload_original_intacto(fila, consumidora):
    """
    O payload que chega na DLQ é idêntico ao enviado — sem alteração.

    A DLQ não é uma lixeira: é um repositório para investigação e
    reprocessamento após a correção do problema que causou a falha.
    Cada campo do payload original deve estar presente e inalterado.
    """
    import json

    sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"
    payload_original = {"sku": sku, "qtd": 5, "defeituoso": True, "origem": "teste-v9"}

    fila.enviar_mensagem(payload_original)

    payload_na_dlq = None

    def capturar_payload_na_dlq():
        nonlocal payload_na_dlq
        for mensagem in fila.receber_da_fila_morta():
            if sku in mensagem["Body"]:
                payload_na_dlq = json.loads(mensagem["Body"])
                return True
        return False

    wait_until(
        capturar_payload_na_dlq,
        timeout=90,
        interval=2,
        message="mensagem não chegou na DLQ para validar o payload",
    )

    assert payload_na_dlq["sku"] == sku
    assert payload_na_dlq["qtd"] == 5
    assert payload_na_dlq["origem"] == "teste-v9"


@pytest.mark.timeout(30)
def test_mensagem_valida_nao_e_enviada_para_dlq(fila, consumidora):
    """
    Uma mensagem sem "defeituoso" é processada com sucesso e NÃO vai
    para a DLQ.

    Demonstra que a DLQ isola apenas poison messages. O fluxo normal
    continua sem interrupção — uma falha pontual não vira indisponibilidade.
    """
    sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"

    fila.enviar_mensagem({"sku": sku, "qtd": 3})  # sem "defeituoso"

    assert_never(
        lambda: fila.mensagem_chegou_na_fila_morta(sku),
        duration=15,
        message="mensagem saudável não deveria ir para a fila morta (DLQ)",
    )
