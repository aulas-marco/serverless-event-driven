"""
Lambda A — Produtor (U1V7: Fan-out)

Publica um evento PedidoCriado no tópico SNS.
UMA chamada publish → o SNS entrega para N assinantes.
O produtor não conhece as filas; conhece apenas o tópico.
"""
import boto3
import json
import os
import uuid
from datetime import datetime, timezone

# Clientes criados fora do handler: reutilizados entre invocações na mesma instância quente.
# AWS_ENDPOINT_URL é lida automaticamente pelo boto3 — aponta para LocalStack ou AWS Real.
_sns = boto3.client("sns", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))

TOPIC_ARN = os.environ["TOPIC_ARN"]  # ARN vem de variável de ambiente — nunca hardcoded


def lambda_handler(event, context):
    pedido = {
        "pedidoId": str(uuid.uuid4()),
        "clienteId": "cliente-42",
        "valor": "199.90",
        "criadoEm": datetime.now(timezone.utc).isoformat(),
    }
    payload = json.dumps(pedido)

    # UMA publicação. O fan-out (entrega para múltiplas filas) acontece aqui,
    # no SNS, via assinaturas configuradas — não neste código.
    _sns.publish(TopicArn=TOPIC_ARN, Message=payload)

    print(f"[PRODUTOR] Publicado PedidoCriado: {payload}")
    return pedido["pedidoId"]
