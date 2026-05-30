"""Snapshots de agregado (U2). Otimização do replay: parte do último snapshot."""
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

from src.U2_event_sourcing.conta import ContaBancaria


def _tabela_snapshots(dynamodb_resource):
    return (dynamodb_resource or boto3.resource(
        "dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))).Table("snapshots")


def gravar_snapshot(dynamodb_resource, store, aggregate_id: str) -> None:
    eventos = store.carregar_por_agregado(aggregate_id)
    conta = ContaBancaria.reconstruir(eventos)
    _tabela_snapshots(dynamodb_resource).put_item(Item={
        "aggregate_id": aggregate_id,
        "saldo": conta.saldo,
        "ultima_sequencia": len(eventos),
    })


def reconstruir_com_snapshot(dynamodb_resource, store, aggregate_id: str) -> Decimal:
    resp = _tabela_snapshots(dynamodb_resource).get_item(Key={"aggregate_id": aggregate_id})
    snap = resp.get("Item")
    if not snap:
        return ContaBancaria.reconstruir(store.carregar_por_agregado(aggregate_id)).saldo
    # Aplica só os eventos posteriores ao snapshot.
    todos = store.carregar_por_agregado(aggregate_id)
    delta = todos[int(snap["ultima_sequencia"]):]
    conta = ContaBancaria()
    conta.saldo = Decimal(str(snap["saldo"]))
    conta.existe = True
    for evento in delta:
        conta.aplicar(evento)
    return conta.saldo
