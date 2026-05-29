"""
Testes da Demo U1V8 — Idempotência com Lambda + DynamoDB

Objetivo: verificar que processar a MESMA mensagem duas vezes
não produz efeito colateral duplicado.

Estes testes invocam o Lambda diretamente (não via SQS),
o que permite controlar o messageId e verificar o DynamoDB
sem depender do event source mapping.

Pré-condição: execute `make up` antes de rodar estes testes.
"""
import json
import time
import uuid

import pytest

from tests.helpers import deploy_lambda, wait_until

TABLE_NAME = "mensagens-processadas"
FUNCTION_NAME = "processa-pedido"
HANDLER_PATH = "src/U1V8_idempotencia/processa_pedido.py"


# ── Fixtures de módulo ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def tabela_controle(dynamodb):
    """Cria a tabela DynamoDB de controle de duplicatas."""
    try:
        dynamodb.create_table(
            TableName=TABLE_NAME,
            AttributeDefinitions=[{"AttributeName": "messageId", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "messageId", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # Aguarda a tabela ficar ACTIVE
        wait_until(
            lambda: dynamodb.describe_table(TableName=TABLE_NAME)["Table"]["TableStatus"] == "ACTIVE",
            timeout=30,
            message="tabela DynamoDB não ficou ACTIVE",
        )
    except dynamodb.exceptions.ResourceInUseException:
        pass  # tabela já existe — ok

    dynamodb.update_time_to_live(
        TableName=TABLE_NAME,
        TimeToLiveSpecification={"Enabled": True, "AttributeName": "expira_em"},
    )
    return TABLE_NAME


@pytest.fixture(scope="module")
def lambda_idempotencia(lam, tabela_controle):
    """Deploy da função processa_pedido no LocalStack."""
    deploy_lambda(
        lambda_client=lam,
        function_name=FUNCTION_NAME,
        source_path=HANDLER_PATH,
        handler="processa_pedido.lambda_handler",
        env_vars={"DYNAMODB_TABLE": TABLE_NAME},
    )
    return FUNCTION_NAME


def _invocar(lam, message_id: str) -> dict:
    """Invoca o Lambda com um payload SQSEvent simulado."""
    payload = {
        "Records": [
            {"body": json.dumps({"messageId": message_id, "valor": "99.90"})}
        ]
    }
    resp = lam.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode(),
    )
    return resp


def _item_existe(dynamodb, message_id: str) -> bool:
    resp = dynamodb.get_item(
        TableName=TABLE_NAME,
        Key={"messageId": {"S": message_id}},
    )
    return "Item" in resp


# ── Testes ────────────────────────────────────────────────────────────────────


def test_primeira_mensagem_e_processada(lam, dynamodb, lambda_idempotencia):
    """
    Uma mensagem nova deve ser processada e registrada no DynamoDB.
    """
    message_id = f"pedido-{uuid.uuid4()}"
    resp = _invocar(lam, message_id)

    assert resp["StatusCode"] == 200
    assert "FunctionError" not in resp

    wait_until(
        lambda: _item_existe(dynamodb, message_id),
        timeout=10,
        message=f"messageId '{message_id}' não foi gravado no DynamoDB",
    )


def test_duplicata_e_descartada(lam, dynamodb, lambda_idempotencia):
    """
    Invocar duas vezes com o MESMO messageId deve:
    - Processar apenas na primeira invocação
    - Descartar silenciosamente na segunda (sem erro, sem duplicata)

    Este é o comportamento esperado sob entrega at-least-once do SQS.
    """
    message_id = f"pedido-{uuid.uuid4()}"

    # Primeira invocação — deve processar
    resp1 = _invocar(lam, message_id)
    assert resp1["StatusCode"] == 200
    assert "FunctionError" not in resp1

    # Segunda invocação — mesma mensagem, deve ser descartada sem erro
    resp2 = _invocar(lam, message_id)
    assert resp2["StatusCode"] == 200
    assert "FunctionError" not in resp2

    # DynamoDB deve ter EXATAMENTE 1 item — não duplicou
    resp = dynamodb.query(
        TableName=TABLE_NAME,
        KeyConditionExpression="messageId = :id",
        ExpressionAttributeValues={":id": {"S": message_id}},
    )
    assert resp["Count"] == 1, (
        f"Esperava 1 item no DynamoDB para messageId={message_id}, "
        f"mas encontrou {resp['Count']} — duplicata escapou!"
    )


def test_item_tem_ttl_configurado(lam, dynamodb, lambda_idempotencia):
    """
    O item de controle deve ter o campo 'expira_em' (TTL),
    garantindo que a tabela não cresça indefinidamente.
    """
    message_id = f"pedido-{uuid.uuid4()}"
    _invocar(lam, message_id)

    wait_until(
        lambda: _item_existe(dynamodb, message_id),
        timeout=10,
        message="item não gravado",
    )

    resp = dynamodb.get_item(
        TableName=TABLE_NAME,
        Key={"messageId": {"S": message_id}},
    )
    item = resp["Item"]
    assert "expira_em" in item, "item de controle deve ter campo expira_em (TTL)"
    expira = int(item["expira_em"]["N"])
    agora = int(time.time())
    assert expira > agora, "expira_em deve ser no futuro"
    # Janela de TTL: entre 1h e 48h
    assert expira - agora < 48 * 3600, "TTL não deve ser excessivamente longo"


def test_putitem_condicional_nao_lanca_excecao_em_duplicata(lam, dynamodb, lambda_idempotencia):
    """
    A ConditionalCheckFailedException deve ser CAPTURADA pelo handler
    e tratada como descarte silencioso — não como erro da função.

    Se o handler não capturasse a exceção, FunctionError apareceria
    na resposta e o SQS recolocaria a mensagem na fila (gerando loop).
    """
    message_id = f"pedido-{uuid.uuid4()}"

    _invocar(lam, message_id)  # Primeira — processa
    resp = _invocar(lam, message_id)  # Segunda — deve descartar sem error

    # FunctionError indica que o Lambda lançou exceção não tratada
    assert "FunctionError" not in resp, (
        "O handler não deve deixar ConditionalCheckFailedException vazar — "
        "isso faria o SQS recolocar a mensagem na fila indefinidamente."
    )
