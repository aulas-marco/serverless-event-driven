import uuid
from decimal import Decimal

import pytest

from tests.aws_builder import ContaBancariaEventStore, TabelaSnapshots
from tests.narracao import narrador
from src.U2_event_sourcing.repositorio import EventStore
from src.U2_event_sourcing.comandos import depositar
from src.U2_event_sourcing.conta import ContaBancaria
from src.U2_event_sourcing.snapshots import gravar_snapshot, reconstruir_com_snapshot


@pytest.fixture(scope="module", autouse=True)
def _demo_banner():
    narrador.demo(
        "U2V8 — Replay e Snapshots",
        "Replay é idempotente; um snapshot encurta o replay sem mudar o resultado.",
    )


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
    narrador.observacao("Replay 2× produz o mesmo saldo (idempotente)", depois=str(s1))
    assert s1 == s2 == Decimal("125")


def test_reconstruir_com_snapshot_bate_com_replay_completo(tabelas, dynamodb_resource):
    store = EventStore(dynamodb_resource)
    conta_id = f"conta-{uuid.uuid4()}"
    depositar(store, conta_id, Decimal("100"))
    gravar_snapshot(dynamodb_resource, store, conta_id)   # tira foto no estado atual
    depositar(store, conta_id, Decimal("10"))             # +10 após o snapshot

    narrador.nota("Snapshot tirado em 100; +10 gravado depois do snapshot.")
    saldo = reconstruir_com_snapshot(dynamodb_resource, store, conta_id)
    completo = ContaBancaria.reconstruir(store.carregar_por_agregado(conta_id)).saldo
    narrador.observacao("Replay a partir do snapshot == replay completo", depois=str(saldo))
    assert saldo == completo == Decimal("110")
