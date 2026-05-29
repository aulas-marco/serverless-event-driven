"""
Lambda — Processa Pedido com Idempotência (U1V8)

Consome mensagens SQS e grava o pedido no DynamoDB.
Usa PutItem condicional para garantir que cada messageId é processado
exatamente uma vez, mesmo sob entrega at-least-once do SQS.

Pegadinha clássica: GetItem + PutItem tem condição de corrida.
A versão correta usa attribute_not_exists(messageId) numa operação atômica.
"""
import boto3
import json
import os
import time

from botocore.exceptions import ClientError

_dynamo = boto3.resource("dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
_table = _dynamo.Table(os.environ.get("DYNAMODB_TABLE", "mensagens-processadas"))


def lambda_handler(event, context):
    for record in event["Records"]:
        pedido = json.loads(record["body"])
        message_id = pedido["messageId"]

        # Checagem ANTES do efeito colateral — essa ordem é invariável.
        if not _reivindicar(message_id):
            print(f"[IDEMPOTENCIA] Duplicata descartada: {message_id}")
            continue

        _processar_pedido(pedido)


def _reivindicar(message_id: str) -> bool:
    """
    Tenta registrar o messageId atomicamente.
    Retorna True se for a primeira vez; False se for duplicata.

    Usa PutItem com ConditionExpression para garantir atomicidade.
    Isso elimina a condição de corrida que existiria com GetItem + PutItem separados:

        Invocação A: get_item → "não existe"
        Invocação B: get_item → "não existe"   ← B leu antes de A gravar
        Invocação A: put_item → grava
        Invocação B: put_item → grava (sobrescreve) → DUPLICATA!

    Com a versão atômica:
        A: put_item condicional → SUCESSO → processa
        B: put_item condicional → ConditionalCheckFailedException → descarta
    """
    agora = int(time.time())
    expira_em = agora + 86_400  # TTL: 24h em segundos epoch

    try:
        _table.put_item(
            Item={
                "messageId": message_id,
                "processado_em": agora,
                "expira_em": expira_em,
            },
            # Grava SOMENTE se o messageId ainda não existir — operação atômica no servidor.
            ConditionExpression="attribute_not_exists(messageId)",
        )
        return True  # Reivindiquei o ID → posso processar
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False  # Já existia → duplicata
        raise


def _processar_pedido(pedido: dict) -> None:
    """Efeito colateral de negócio. Só é chamado para mensagens novas."""
    print(f"[NEGOCIO] Processando pedido: {pedido['messageId']}")
