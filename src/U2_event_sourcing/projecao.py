"""Projeção CQRS (U2): mantém a tabela de leitura `saldo_atual`.

A Lambda é acionada por DynamoDB Streams sobre a tabela `eventos`: cada evento
novo ajusta o saldo projetado. O lado de consulta lê apenas de `saldo_atual`.
"""
import json
import os
from decimal import Decimal

import boto3


def _recurso_dynamodb():
    """Cria o recurso DynamoDB lendo as variáveis de ambiente no momento da chamada.

    Inicialização lazy: evita capturar endpoint incorreto em módulo cacheado.
    """
    return boto3.resource("dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))


def _tabela_saldo(dynamodb_resource=None):
    ddb = dynamodb_resource or _recurso_dynamodb()
    return ddb.Table(os.environ.get("TABELA_SALDO", "saldo_atual"))


def lambda_handler(event, context):
    tabela = _tabela_saldo()
    for registro in event["Records"]:
        if registro["eventName"] != "INSERT":
            continue
        novo = registro["dynamodb"]["NewImage"]
        conta_id = novo["aggregate_id"]["S"]
        tipo = novo["tipo"]["S"]
        payload = json.loads(novo["payload"]["S"])
        delta = Decimal(str(payload.get("valor", "0")))
        if tipo == "DepositoRealizado":
            _aplicar(tabela, conta_id, delta)
        elif tipo == "SaqueRealizado":
            _aplicar(tabela, conta_id, -delta)
        elif tipo == "ContaCriada":
            _aplicar(tabela, conta_id, Decimal("0"))


def _aplicar(tabela, conta_id: str, delta: Decimal) -> None:
    tabela.update_item(
        Key={"conta_id": conta_id},
        UpdateExpression="SET saldo = if_not_exists(saldo, :zero) + :d",
        ExpressionAttributeValues={":d": delta, ":zero": Decimal("0")},
    )


def obter_saldo(conta_id: str, dynamodb_resource=None) -> Decimal:
    tabela = _tabela_saldo(dynamodb_resource)
    item = tabela.get_item(Key={"conta_id": conta_id}).get("Item")
    return Decimal(str(item["saldo"])) if item else Decimal("0")
