"""
Testes da Demo U1V8 — Idempotência com Lambda + DynamoDB

O que estes testes verificam:
    Processar a MESMA mensagem duas vezes não produz efeito colateral
    duplicado. O PutItem condicional no DynamoDB garante que apenas a
    primeira entrega produz efeito — as seguintes são descartadas.

Como funcionam:
    Invocam a Lambda diretamente com um evento SQS simulado.
    Isso isola o comportamento de idempotência sem depender do
    event source mapping.

O que NÃO está aqui:
    Criação de tabela DynamoDB, deploy da Lambda, formato do evento SQS —
    isso está em TabelaDeDeduplicacao e ProcessadorDePedidos (aws_builder.py).
"""
import time
import uuid

import pytest

from tests.aws_builder import ProcessadorDePedidos, TabelaDeDeduplicacao
from tests.helpers import wait_until
from tests.narracao import narrador


@pytest.fixture(scope="module", autouse=True)
def _demo_banner():
    narrador.demo(
        "U1V8 — Idempotência com Lambda + DynamoDB",
        "Processar a MESMA mensagem 2× grava só 1 registro (PutItem condicional).",
    )


@pytest.fixture(scope="module")
def tabela(dynamodb) -> TabelaDeDeduplicacao:
    """Cria (ou reutiliza) a tabela de deduplicação para o módulo."""
    return TabelaDeDeduplicacao(dynamodb)


@pytest.fixture(scope="module")
def processador(lam, tabela) -> ProcessadorDePedidos:
    """Faz o deploy da Lambda processa_pedido e a conecta à tabela."""
    return ProcessadorDePedidos(lam, tabela.NOME)


# ── Testes ────────────────────────────────────────────────────────────────────


def test_primeira_entrega_processa_e_registra_no_dynamodb(processador, tabela):
    """
    Caminho feliz: uma mensagem nova é processada e registrada.
    O messageId aparece na tabela de controle após a invocação.
    """
    message_id = f"pedido-{uuid.uuid4()}"

    resposta = processador.processar(message_id)

    assert resposta["StatusCode"] == 200
    assert not processador.retornou_erro(resposta)

    wait_until(
        lambda: tabela.pedido_foi_registrado(message_id),
        timeout=10,
        message=f"messageId '{message_id}' não foi gravado no DynamoDB",
    )


def test_segunda_entrega_do_mesmo_pedido_e_ignorada(processador, tabela):
    """
    Duas entregas do mesmo pedido → exatamente 1 registro no DynamoDB.

    Simula o at-least-once do SQS: a mesma mensagem pode chegar mais de
    uma vez por timeout de visibilidade, falha de rede ou retry automático.
    Sem idempotência, a segunda entrega geraria cobrança dupla, e-mail
    duplicado ou baixa de estoque incorreta.
    """
    message_id = f"pedido-{uuid.uuid4()}"

    resposta_1 = processador.processar(message_id)
    resposta_2 = processador.processar(message_id)  # mesma mensagem

    assert not processador.retornou_erro(resposta_1), "primeira entrega não deve falhar"
    assert not processador.retornou_erro(resposta_2), "segunda entrega não deve falhar"

    narrador.nota("2ª entrega do mesmo messageId: a escrita condicional falha e a duplicata é descartada.")
    narrador.observacao("Exatamente 1 registro permanece no DynamoDB", depois=message_id)

    assert tabela.contar_registros(message_id) == 1, (
        f"Esperava 1 registro (messageId={message_id}), "
        f"mas encontrou {tabela.contar_registros(message_id)}. "
        "A duplicata escapou!"
    )


def test_registro_de_controle_tem_data_de_expiracao(processador, tabela):
    """
    O registro de controle deve ter o campo 'expira_em' (TTL).

    TTL (Time to Live): o DynamoDB apaga o item automaticamente após o
    timestamp configurado. Sem TTL, a tabela cresceria indefinidamente.
    O DynamoDB não apaga no segundo exato — pode levar até 48h após o TTL.
    """
    message_id = f"pedido-{uuid.uuid4()}"
    processador.processar(message_id)

    wait_until(
        lambda: tabela.pedido_foi_registrado(message_id),
        timeout=10,
        message="registro não encontrado no DynamoDB",
    )

    registro = tabela.obter_registro(message_id)

    assert "expira_em" in registro, (
        "O registro deve ter o campo 'expira_em' para que o TTL funcione."
    )
    timestamp_de_expiracao = int(registro["expira_em"]["N"])
    agora = int(time.time())

    assert timestamp_de_expiracao > agora, "expira_em deve ser um timestamp no futuro"
    assert timestamp_de_expiracao - agora < 48 * 3600, "TTL não deve ultrapassar 48h"


def test_duplicata_nao_gera_erro_na_funcao(processador, tabela):
    """
    A ConditionalCheckFailedException do DynamoDB deve ser tratada
    internamente — não pode vazar como FunctionError.

    Se vazasse: o SQS interpretaria como falha de processamento,
    recolocaria a mensagem na fila e geraria um loop infinito até
    a DLQ ser acionada. A exceção é um sinal esperado de "duplicata" —
    não um erro de sistema.
    """
    message_id = f"pedido-{uuid.uuid4()}"

    processador.processar(message_id)
    resposta_duplicata = processador.processar(message_id)

    assert not processador.retornou_erro(resposta_duplicata), (
        "FunctionError presente: o handler deixou a ConditionalCheckFailedException "
        "vazar. Isso faria o SQS recolocar a mensagem na fila indefinidamente."
    )
