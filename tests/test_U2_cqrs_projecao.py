import uuid
from decimal import Decimal

import pytest

from tests.aws_builder import ContaBancariaEventStore, ProjecaoSaldo
from tests.helpers import wait_until
from src.U2_event_sourcing.repositorio import EventStore
from src.U2_event_sourcing.comandos import depositar, transferir
from src.U2_event_sourcing.conta import ContaBancaria


@pytest.fixture(scope="module")
def projecao(dynamodb_resource, lam):
    ContaBancariaEventStore(dynamodb_resource)      # garante tabela eventos + stream
    return ProjecaoSaldo(dynamodb_resource, lam)


def test_projecao_reflete_evento_apos_propagacao_do_stream(projecao, dynamodb_resource):
    store = EventStore(dynamodb_resource)
    conta_id = f"conta-{uuid.uuid4()}"
    depositar(store, conta_id, Decimal("80"))

    wait_until(
        lambda: projecao.saldo(conta_id) == Decimal("80"),
        timeout=60,
        message="saldo_atual não refletiu o depósito via DynamoDB Streams",
    )


def test_transferir_move_saldo_entre_contas_atomicamente(projecao, dynamodb_resource):
    store = EventStore(dynamodb_resource)
    origem = f"conta-{uuid.uuid4()}"
    destino = f"conta-{uuid.uuid4()}"
    depositar(store, origem, Decimal("100"))

    transferir(store, origem, destino, Decimal("40"))

    assert ContaBancaria.reconstruir(store.carregar_por_agregado(origem)).saldo == Decimal("60")
    assert ContaBancaria.reconstruir(store.carregar_por_agregado(destino)).saldo == Decimal("40")
