from decimal import Decimal

from src.U2_event_sourcing.eventos import (
    ContaCriada, DepositoRealizado, SaqueRealizado, evento_de_item, item_de_evento,
)
from src.U2_event_sourcing.conta import ContaBancaria


def test_evento_serializa_e_desserializa_preservando_tipo_e_dados():
    evento = DepositoRealizado(aggregate_id="conta-1", valor=Decimal("100.50"))
    item = item_de_evento(evento, sequencia=1, criado_em=1717000000)

    assert item["aggregate_id"] == "conta-1"
    assert item["sequencia"] == 1
    assert item["tipo"] == "DepositoRealizado"

    reconstruido = evento_de_item(item)
    assert isinstance(reconstruido, DepositoRealizado)
    assert reconstruido.valor == Decimal("100.50")
    assert reconstruido.aggregate_id == "conta-1"


def test_reconstruir_faz_fold_dos_eventos_ate_o_saldo():
    eventos = [
        ContaCriada(aggregate_id="conta-1"),
        DepositoRealizado(aggregate_id="conta-1", valor=Decimal("100")),
        SaqueRealizado(aggregate_id="conta-1", valor=Decimal("30")),
    ]
    conta = ContaBancaria.reconstruir(eventos)
    assert conta.existe is True
    assert conta.saldo == Decimal("70")


def test_conta_sem_eventos_nao_existe():
    conta = ContaBancaria.reconstruir([])
    assert conta.existe is False
    assert conta.saldo == Decimal("0")


import uuid
import pytest
from tests.aws_builder import ContaBancariaEventStore
from src.U2_event_sourcing.repositorio import EventStore


@pytest.fixture(scope="module")
def event_store_table(dynamodb_resource):
    return ContaBancariaEventStore(dynamodb_resource)


def test_append_grava_em_sequencia_crescente_e_carrega_ordenado(event_store_table, dynamodb_resource):
    store = EventStore(dynamodb_resource)
    conta_id = f"conta-{uuid.uuid4()}"

    s1 = store.append(conta_id, ContaCriada(aggregate_id=conta_id))
    s2 = store.append(conta_id, DepositoRealizado(aggregate_id=conta_id, valor=Decimal("100")))

    assert (s1, s2) == (1, 2)
    eventos = store.carregar_por_agregado(conta_id)
    assert [type(e).__name__ for e in eventos] == ["ContaCriada", "DepositoRealizado"]


def test_append_e_idempotente_por_sequencia_condicional(event_store_table, dynamodb_resource):
    """Gravar na mesma sequência de novo deve falhar (append-only protegido)."""
    from botocore.exceptions import ClientError
    store = EventStore(dynamodb_resource)
    conta_id = f"conta-{uuid.uuid4()}"
    store.append(conta_id, ContaCriada(aggregate_id=conta_id))

    with pytest.raises(ClientError) as exc:
        store._gravar_em_sequencia(conta_id, DepositoRealizado(aggregate_id=conta_id, valor=Decimal("1")), sequencia=1)
    assert exc.value.response["Error"]["Code"] == "ConditionalCheckFailedException"


from src.U2_event_sourcing.comandos import depositar, sacar, SaldoInsuficiente


def test_depositar_e_sacar_atualizam_o_saldo_reconstruido(event_store_table, dynamodb_resource):
    store = EventStore(dynamodb_resource)
    conta_id = f"conta-{uuid.uuid4()}"

    depositar(store, conta_id, Decimal("200"))
    sacar(store, conta_id, Decimal("50"))

    conta = ContaBancaria.reconstruir(store.carregar_por_agregado(conta_id))
    assert conta.saldo == Decimal("150")


def test_sacar_alem_do_saldo_levanta_saldo_insuficiente(event_store_table, dynamodb_resource):
    store = EventStore(dynamodb_resource)
    conta_id = f"conta-{uuid.uuid4()}"
    depositar(store, conta_id, Decimal("10"))

    with pytest.raises(SaldoInsuficiente):
        sacar(store, conta_id, Decimal("999"))
