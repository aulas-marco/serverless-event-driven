"""
Testes da Demo U1V8 — Idempotência com Lambda + DynamoDB

O que estes testes verificam:
    Processar a MESMA mensagem duas vezes não produz efeito colateral
    duplicado. Isso é necessário porque o SQS entrega at-least-once:
    a mesma mensagem pode chegar mais de uma vez.

Como estes testes funcionam:
    Invocam a Lambda diretamente (não via SQS), passando um payload
    no formato SQSEvent simulado. Isso permite controlar o messageId
    e verificar o DynamoDB sem depender do event source mapping.

Pré-condição: `make up` (LocalStack rodando).
"""
import json
import time
import uuid

import pytest

from tests.helpers import deploy_lambda, wait_until

# ── Constantes ────────────────────────────────────────────────────────────────

NOME_DA_TABELA = "mensagens-processadas"
NOME_DA_FUNCAO = "processa-pedido"
CAMINHO_DO_HANDLER = "src/U1V8_idempotencia/processa_pedido.py"

# ── Infraestrutura dos testes (fixtures) ──────────────────────────────────────


@pytest.fixture(scope="module")
def tabela_de_deduplicacao(dynamodb):
    """
    Cria a tabela DynamoDB que armazena os messageIds já processados.
    TTL ativado no campo 'expira_em': o DynamoDB apaga o item
    automaticamente após 24h, evitando que a tabela cresça indefinidamente.
    """
    try:
        dynamodb.create_table(
            TableName=NOME_DA_TABELA,
            AttributeDefinitions=[{"AttributeName": "messageId", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "messageId", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        wait_until(
            lambda: dynamodb.describe_table(TableName=NOME_DA_TABELA)
                             ["Table"]["TableStatus"] == "ACTIVE",
            timeout=30,
            message="tabela DynamoDB não ficou ACTIVE",
        )
    except dynamodb.exceptions.ResourceInUseException:
        pass  # tabela já existe — ok em execuções repetidas

    dynamodb.update_time_to_live(
        TableName=NOME_DA_TABELA,
        TimeToLiveSpecification={"Enabled": True, "AttributeName": "expira_em"},
    )
    return NOME_DA_TABELA


@pytest.fixture(scope="module")
def funcao_com_idempotencia(lam, tabela_de_deduplicacao):
    """
    Faz o deploy da função processa_pedido.py no LocalStack.
    A variável DYNAMODB_TABLE é injetada via ambiente para que a
    função saiba qual tabela usar — sem hardcode no código.
    """
    deploy_lambda(
        lambda_client=lam,
        function_name=NOME_DA_FUNCAO,
        source_path=CAMINHO_DO_HANDLER,
        handler="processa_pedido.lambda_handler",
        env_vars={"DYNAMODB_TABLE": NOME_DA_TABELA},
    )
    return NOME_DA_FUNCAO


# ── Funções auxiliares ────────────────────────────────────────────────────────


def _invocar_lambda_com_pedido(lam, message_id: str) -> dict:
    """
    Invoca a Lambda com um evento SQS simulado.
    O formato imita exatamente o que o SQS enviaria via event source mapping:
    um dicionário com uma lista 'Records', cada um com um campo 'body'.
    """
    evento_sqs_simulado = {
        "Records": [
            {"body": json.dumps({"messageId": message_id, "valor": "99.90"})}
        ]
    }
    return lam.invoke(
        FunctionName=NOME_DA_FUNCAO,
        InvocationType="RequestResponse",
        Payload=json.dumps(evento_sqs_simulado).encode(),
    )


def _pedido_foi_registrado(dynamodb, message_id: str) -> bool:
    """Verifica se o messageId foi gravado na tabela de controle."""
    resposta = dynamodb.get_item(
        TableName=NOME_DA_TABELA,
        Key={"messageId": {"S": message_id}},
    )
    return "Item" in resposta


# ── Testes ────────────────────────────────────────────────────────────────────


def test_primeira_entrega_processa_e_registra_no_dynamodb(lam, dynamodb, funcao_com_idempotencia):
    """
    Uma mensagem nova deve ser processada e ter seu messageId registrado
    na tabela de controle do DynamoDB.

    Este é o caminho feliz: primeira entrega, sem duplicata.
    """
    message_id = f"pedido-{uuid.uuid4()}"

    resposta = _invocar_lambda_com_pedido(lam, message_id)

    assert resposta["StatusCode"] == 200, "Lambda deve retornar HTTP 200"
    assert "FunctionError" not in resposta, "Lambda não deve lançar exceção"

    wait_until(
        lambda: _pedido_foi_registrado(dynamodb, message_id),
        timeout=10,
        message=f"messageId '{message_id}' não foi gravado no DynamoDB após o processamento",
    )


def test_segunda_entrega_do_mesmo_pedido_e_ignorada(lam, dynamodb, funcao_com_idempotencia):
    """
    Invocar a Lambda duas vezes com o MESMO messageId deve resultar
    em exatamente UM registro no DynamoDB — a segunda entrega é descartada.

    Isso simula o comportamento at-least-once do SQS:
    a mesma mensagem pode chegar mais de uma vez (ex: timeout de visibilidade,
    falha de rede, retry automático). Sem idempotência, o pedido seria
    cobrado duas vezes, o e-mail enviado duas vezes, etc.
    """
    message_id = f"pedido-{uuid.uuid4()}"

    # Primeira entrega — deve processar normalmente
    resposta_1 = _invocar_lambda_com_pedido(lam, message_id)
    assert resposta_1["StatusCode"] == 200
    assert "FunctionError" not in resposta_1

    # Segunda entrega — mesmo messageId, deve ser descartada silenciosamente
    resposta_2 = _invocar_lambda_com_pedido(lam, message_id)
    assert resposta_2["StatusCode"] == 200
    assert "FunctionError" not in resposta_2

    # Prova: DynamoDB deve ter EXATAMENTE 1 registro para este messageId
    resultado = dynamodb.query(
        TableName=NOME_DA_TABELA,
        KeyConditionExpression="messageId = :id",
        ExpressionAttributeValues={":id": {"S": message_id}},
    )
    assert resultado["Count"] == 1, (
        f"Esperava 1 registro no DynamoDB (messageId={message_id}), "
        f"mas encontrou {resultado['Count']}. A duplicata escapou!"
    )


def test_registro_de_controle_tem_data_de_expiracao(lam, dynamodb, funcao_com_idempotencia):
    """
    O registro de controle no DynamoDB deve ter o campo 'expira_em' (TTL).

    Sem TTL, a tabela cresceria indefinidamente. Com TTL, o DynamoDB
    apaga os registros antigos automaticamente. O campo armazena um
    timestamp Unix futuro; o DynamoDB apaga o item após esse instante.

    Importante: o DynamoDB não apaga no segundo exato — pode levar
    até 48h após o TTL. Para garantias fortes, use condições no código.
    """
    message_id = f"pedido-{uuid.uuid4()}"
    _invocar_lambda_com_pedido(lam, message_id)

    wait_until(
        lambda: _pedido_foi_registrado(dynamodb, message_id),
        timeout=10,
        message="registro não encontrado no DynamoDB",
    )

    resposta = dynamodb.get_item(
        TableName=NOME_DA_TABELA,
        Key={"messageId": {"S": message_id}},
    )
    registro = resposta["Item"]

    assert "expira_em" in registro, (
        "O registro de controle deve ter o campo 'expira_em' para que o TTL funcione."
    )

    timestamp_expiracao = int(registro["expira_em"]["N"])
    agora = int(time.time())

    assert timestamp_expiracao > agora, "expira_em deve ser um timestamp no futuro"
    assert timestamp_expiracao - agora < 48 * 3600, (
        "TTL não deve ser excessivamente longo (máximo esperado: 48h)"
    )


def test_duplicata_nao_gera_erro_na_funcao(lam, dynamodb, funcao_com_idempotencia):
    """
    A ConditionalCheckFailedException do DynamoDB deve ser CAPTURADA
    internamente — a Lambda não deve deixá-la vazar como FunctionError.

    Por quê isso importa: se a exceção vazasse, o SQS interpretaria como
    falha de processamento e recolocaria a mensagem na fila. Isso geraria
    um loop infinito de reprocessamentos até a DLQ ser acionada.

    A exceção é um sinal esperado de "duplicata detectada" — não um erro.
    """
    message_id = f"pedido-{uuid.uuid4()}"

    _invocar_lambda_com_pedido(lam, message_id)          # primeira — processa
    resposta_duplicata = _invocar_lambda_com_pedido(lam, message_id)  # segunda — descarta

    assert "FunctionError" not in resposta_duplicata, (
        "FunctionError indica exceção não tratada. "
        "O handler deve capturar ConditionalCheckFailedException e retornar "
        "normalmente — caso contrário, o SQS recoloca a mensagem na fila."
    )
