import uuid
from decimal import Decimal

import pytest

from tests.aws_builder import ContaBancariaEventStore, TabelaSnapshots
from src.U2_event_sourcing.repositorio import EventStore
from src.U2_event_sourcing.comandos import depositar
from src.U2_event_sourcing.conta import ContaBancaria
from src.U2_event_sourcing.snapshots import gravar_snapshot, reconstruir_com_snapshot


@pytest.fixture(scope="module")
def tabelas(dynamodb_resource):
    return ContaBancariaEventStore(dynamodb_resource), TabelaSnapshots(dynamodb_resource)


def test_replay_e_idempotente(tabelas, dynamodb_resource):
    store = EventStore(dynamodb_resource)
    conta_id = f"conta-{uuid.uuid4()}"
    depositar(store, conta_id, Decimal("100"))
    depositar(store, conta_id, Decimal("25"))

    s1 = ContaBancaria.reconstruir(store.carregar_por_agregado(conta_id)).saldo
    s2 = ContaBancaria.reconstruir(store.carregar_por_agregado(conta_id)).saldo
    assert s1 == s2 == Decimal("125")


def test_reconstruir_com_snapshot_bate_com_replay_completo(tabelas, dynamodb_resource):
    store = EventStore(dynamodb_resource)
    conta_id = f"conta-{uuid.uuid4()}"
    depositar(store, conta_id, Decimal("100"))
    gravar_snapshot(dynamodb_resource, store, conta_id)   # tira foto no estado atual
    depositar(store, conta_id, Decimal("10"))             # +10 após o snapshot

    saldo = reconstruir_com_snapshot(dynamodb_resource, store, conta_id)
    completo = ContaBancaria.reconstruir(store.carregar_por_agregado(conta_id)).saldo
    assert saldo == completo == Decimal("110")
