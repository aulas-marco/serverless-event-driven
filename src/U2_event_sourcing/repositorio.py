"""Event store append-only sobre DynamoDB (U2).

Garante atomicidade do append com ConditionExpression na chave composta:
nunca sobrescreve uma sequência já gravada (concorrência otimista).
"""
import os
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

from src.U2_event_sourcing.eventos import evento_de_item, item_de_evento


class EventStore:
    def __init__(self, dynamodb_resource=None, nome_tabela: str = "eventos"):
        self._dynamodb = dynamodb_resource or boto3.resource(
            "dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL")
        )
        self._tabela = self._dynamodb.Table(nome_tabela)

    def _proxima_sequencia(self, aggregate_id: str) -> int:
        resp = self._tabela.query(
            KeyConditionExpression=Key("aggregate_id").eq(aggregate_id),
            ScanIndexForward=False,
            Limit=1,
        )
        itens = resp["Items"]
        return int(itens[0]["sequencia"]) + 1 if itens else 1

    def append(self, aggregate_id: str, evento) -> int:
        sequencia = self._proxima_sequencia(aggregate_id)
        self._gravar_em_sequencia(aggregate_id, evento, sequencia)
        return sequencia

    def _gravar_em_sequencia(self, aggregate_id: str, evento, sequencia: int) -> None:
        item = item_de_evento(evento, sequencia=sequencia, criado_em=int(time.time()))
        # Append atômico: só grava se (aggregate_id, sequencia) ainda não existe.
        self._tabela.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(sequencia)",
        )

    def carregar_por_agregado(self, aggregate_id: str) -> list:
        resp = self._tabela.query(
            KeyConditionExpression=Key("aggregate_id").eq(aggregate_id),
            ScanIndexForward=True,
        )
        return [evento_de_item(item) for item in resp["Items"]]
