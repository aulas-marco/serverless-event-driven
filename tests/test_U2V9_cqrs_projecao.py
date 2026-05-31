import uuid
from decimal import Decimal

import pytest

from tests.aws_builder import ContaBancariaEventStore, ProjecaoSaldo
from tests.helpers import wait_until
from tests.narracao import narrador
from src.U2_event_sourcing.repositorio import EventStore
from src.U2_event_sourcing.comandos import depositar, transferir
from src.U2_event_sourcing.conta import ContaBancaria


@pytest.fixture(scope="module", autouse=True)
def _demo_banner():
    narrador.demo(
        "U2V9 — CQRS e Projeção via DynamoDB Streams",
        "O evento gravado em `eventos` propaga para o modelo de leitura `saldo_atual`.",
    )


@pytest.fixture(scope="module")
def projecao(dynamodb_resource, lam):
    ContaBancariaEventStore(dynamodb_resource)      # garante tabela eventos + stream
    return ProjecaoSaldo(dynamodb_resource, lam)


def test_projecao_reflete_evento_apos_propagacao_do_stream(projecao, dynamodb_resource):
    store = EventStore(dynamodb_resource)
    conta_id = f"conta-{uuid.uuid4()}"
    depositar(store, conta_id, Decimal("80"))
    narrador.evento("DepositoRealizado gravado em `eventos`", {"conta": conta_id, "valor": "80"})
    narrador.nota("O DynamoDB Stream aciona a Lambda de projeção de forma assíncrona...")

    wait_until(
        lambda: projecao.saldo(conta_id) == Decimal("80"),
        timeout=60,
        message="saldo_atual não refletiu o depósito via DynamoDB Streams",
    )
    narrador.observacao("Projeção `saldo_atual` refletiu o evento", antes="0", depois="80")


def test_transferir_move_saldo_entre_contas_atomicamente(projecao, dynamodb_resource):
    store = EventStore(dynamodb_resource)
    origem = f"conta-{uuid.uuid4()}"
    destino = f"conta-{uuid.uuid4()}"
    depositar(store, origem, Decimal("100"))

    narrador.evento("transferir 40 (origem → destino) via TransactWriteItems", {"origem": origem, "destino": destino, "valor": "40"})
    transferir(store, origem, destino, Decimal("40"))
    narrador.observacao("Transferência atômica concluída (saldos origem / destino)", antes="100 / 0", depois="60 / 40")

    assert ContaBancaria.reconstruir(store.carregar_por_agregado(origem)).saldo == Decimal("60")
    assert ContaBancaria.reconstruir(store.carregar_por_agregado(destino)).saldo == Decimal("40")
