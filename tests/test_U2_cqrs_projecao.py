import uuid
from decimal import Decimal

import pytest

from tests.aws_builder import ContaBancariaEventStore, ProjecaoSaldo
from tests.helpers import wait_until
from src.U2_event_sourcing.repositorio import EventStore
from src.U2_event_sourcing.comandos import depositar


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
