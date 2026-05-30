"""Handlers de comando da Conta Bancária (U2). Comandos só ANEXAM eventos."""
import os
import time
from decimal import Decimal

import boto3

from src.U2_event_sourcing.conta import ContaBancaria
from src.U2_event_sourcing.eventos import (
    ContaCriada, DepositoRealizado, SaqueRealizado,
    item_de_evento,
)


class SaldoInsuficiente(Exception):
    """Levantada quando um saque excede o saldo reconstruído."""


def _garantir_conta(store, conta_id: str) -> ContaBancaria:
    eventos = store.carregar_por_agregado(conta_id)
    conta = ContaBancaria.reconstruir(eventos)
    if not conta.existe:
        store.append(conta_id, ContaCriada(aggregate_id=conta_id))
    return conta


def depositar(store, conta_id: str, valor: Decimal) -> None:
    _garantir_conta(store, conta_id)
    store.append(conta_id, DepositoRealizado(aggregate_id=conta_id, valor=valor))


def sacar(store, conta_id: str, valor: Decimal) -> None:
    conta = ContaBancaria.reconstruir(store.carregar_por_agregado(conta_id))
    if valor > conta.saldo:
        raise SaldoInsuficiente(
            f"Saque de {valor} excede o saldo de {conta.saldo} (conta {conta_id})"
        )
    store.append(conta_id, SaqueRealizado(aggregate_id=conta_id, valor=valor))


def transferir(store, origem: str, destino: str, valor: Decimal) -> None:
    """Saque na origem + depósito no destino numa única transação no event store."""
    conta_origem = ContaBancaria.reconstruir(store.carregar_por_agregado(origem))
    if valor > conta_origem.saldo:
        raise SaldoInsuficiente(
            f"Transferência de {valor} excede o saldo de {conta_origem.saldo} (conta {origem})"
        )
    _garantir_conta(store, destino)

    seq_origem = store._proxima_sequencia(origem)
    seq_destino = store._proxima_sequencia(destino)
    agora = int(time.time())
    item_saque = item_de_evento(SaqueRealizado(aggregate_id=origem, valor=valor), seq_origem, agora)
    item_deposito = item_de_evento(DepositoRealizado(aggregate_id=destino, valor=valor), seq_destino, agora)

    cliente = boto3.client("dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
    cliente.transact_write_items(TransactItems=[
        {"Put": {"TableName": "eventos", "Item": _para_dynamo(item_saque),
                 "ConditionExpression": "attribute_not_exists(sequencia)"}},
        {"Put": {"TableName": "eventos", "Item": _para_dynamo(item_deposito),
                 "ConditionExpression": "attribute_not_exists(sequencia)"}},
    ])


def _para_dynamo(item: dict) -> dict:
    """Converte um item de resource (tipos Python) para o formato do client low-level."""
    return {
        "aggregate_id": {"S": item["aggregate_id"]},
        "sequencia": {"N": str(item["sequencia"])},
        "tipo": {"S": item["tipo"]},
        "payload": {"S": item["payload"]},
        "criado_em": {"N": str(item["criado_em"])},
    }
