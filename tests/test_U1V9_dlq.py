"""
Testes da Demo U1V9 — DLQ e Resiliência

Objetivo: verificar que uma poison message (mensagem que sempre falha)
é roteada para a DLQ após maxReceiveCount tentativas, sem bloquear
o processamento de mensagens saudáveis.

Estes testes usam event source mapping (SQS → Lambda) para simular
o comportamento real de produção, incluindo o ciclo de retry.

Pré-condição: execute `make up` antes de rodar estes testes.

Atenção: estes testes levam ~35s por cenário (3 tentativas × ~10s de
visibility timeout). Isso é intencional — estamos observando o comportamento
real do SQS, não simulando com mocks.
"""
import json
import uuid

import pytest

from tests.helpers import deploy_lambda, wait_until, assert_never

FUNCTION_NAME = "consumidora-b"
HANDLER_PATH = "src/U1V9_dlq/consumidora_b.py"
FILA_PRINCIPAL = "fila-estoque-v9"
FILA_DLQ = "fila-estoque-v9-dlq"
VISIBILITY_TIMEOUT = 10  # segundos — controla o intervalo entre tentativas


# ── Fixtures de módulo ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def filas_v9(sqs) -> dict:
    """
    Cria a fila principal com DLQ vinculada.
    maxReceiveCount=3: após 3 recepções com falha, roteia para a DLQ.
    VisibilityTimeout=10s: intervalo entre as tentativas (curto para testes).
    """
    dlq_url = sqs.create_queue(QueueName=FILA_DLQ)["QueueUrl"]
    dlq_arn = sqs.get_queue_attributes(
        QueueUrl=dlq_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    import json as _json
    redrive = _json.dumps({"deadLetterTargetArn": dlq_arn, "maxReceiveCount": "3"})
    fila_url = sqs.create_queue(
        QueueName=FILA_PRINCIPAL,
        Attributes={
            "VisibilityTimeout": str(VISIBILITY_TIMEOUT),
            "RedrivePolicy": redrive,
        },
    )["QueueUrl"]

    return {"fila_url": fila_url, "dlq_url": dlq_url}


@pytest.fixture(scope="module")
def lambda_dlq(lam, filas_v9) -> str:
    """Deploy da consumidora_b com a falha proposital ativa."""
    deploy_lambda(
        lambda_client=lam,
        function_name=FUNCTION_NAME,
        source_path=HANDLER_PATH,
        handler="consumidora_b.lambda_handler",
    )

    fila_arn = _get_queue_arn(lam, filas_v9["fila_url"])
    _criar_esm(lam, FUNCTION_NAME, fila_arn)
    return FUNCTION_NAME


def _get_queue_arn(lam, fila_url: str) -> str:
    import boto3, os
    sqs = boto3.client(
        "sqs",
        endpoint_url=os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566"),
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    return sqs.get_queue_attributes(
        QueueUrl=fila_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]


def _criar_esm(lam, function_name: str, fila_arn: str) -> None:
    """Cria o Event Source Mapping SQS → Lambda."""
    try:
        lam.create_event_source_mapping(
            EventSourceArn=fila_arn,
            FunctionName=function_name,
            BatchSize=1,
            Enabled=True,
        )
    except lam.exceptions.ResourceConflictException:
        pass  # ESM já existe


# ── Testes ────────────────────────────────────────────────────────────────────


@pytest.mark.timeout(120)
def test_poison_message_vai_para_dlq(sqs, filas_v9, lambda_dlq):
    """
    Uma mensagem com "defeituoso": true deve:
    1. Ser recebida pela Lambda 3 vezes (maxReceiveCount=3)
    2. Falhar todas as vezes (RuntimeError)
    3. Ser roteada para a DLQ na 4ª recepção

    O timeout do teste é 120s para acomodar os 3 ciclos de retry
    (3 × ~10s de visibility timeout + margem de processamento).
    """
    sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"
    sqs.send_message(
        QueueUrl=filas_v9["fila_url"],
        MessageBody=json.dumps({"sku": sku, "qtd": 1, "defeituoso": True}),
    )

    def mensagem_na_dlq():
        resp = sqs.receive_message(
            QueueUrl=filas_v9["dlq_url"],
            MaxNumberOfMessages=1,
            VisibilityTimeout=5,
        )
        return any(sku in m["Body"] for m in resp.get("Messages", []))

    wait_until(
        mensagem_na_dlq,
        timeout=90,
        interval=2,
        message="poison message não chegou na DLQ no tempo esperado",
    )


@pytest.mark.timeout(120)
def test_payload_preservado_na_dlq(sqs, filas_v9, lambda_dlq):
    """
    O payload original deve chegar na DLQ intacto — byte a byte.
    A DLQ não perde dados; ela isola a mensagem problemática para
    inspeção e possível reprocessamento posterior.
    """
    sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"
    payload_original = {"sku": sku, "qtd": 5, "defeituoso": True, "origem": "teste-v9"}
    sqs.send_message(
        QueueUrl=filas_v9["fila_url"],
        MessageBody=json.dumps(payload_original),
    )

    capturado = None

    def capturar_dlq():
        nonlocal capturado
        resp = sqs.receive_message(
            QueueUrl=filas_v9["dlq_url"],
            MaxNumberOfMessages=10,
            VisibilityTimeout=5,
        )
        for m in resp.get("Messages", []):
            if sku in m["Body"]:
                capturado = json.loads(m["Body"])
                return True
        return False

    wait_until(capturar_dlq, timeout=90, interval=2, message="mensagem não chegou na DLQ")

    assert capturado["sku"] == sku
    assert capturado["qtd"] == 5
    assert capturado["origem"] == "teste-v9"


@pytest.mark.timeout(30)
def test_mensagem_saudavel_nao_vai_para_dlq(sqs, filas_v9, lambda_dlq):
    """
    Uma mensagem sem "defeituoso" não deve ir para a DLQ.
    Demonstra que a DLQ isola apenas poison messages,
    sem afetar o fluxo normal.
    """
    sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"
    sqs.send_message(
        QueueUrl=filas_v9["fila_url"],
        MessageBody=json.dumps({"sku": sku, "qtd": 3}),  # sem "defeituoso"
    )

    def na_dlq():
        resp = sqs.receive_message(
            QueueUrl=filas_v9["dlq_url"],
            MaxNumberOfMessages=10,
        )
        return any(sku in m["Body"] for m in resp.get("Messages", []))

    assert_never(
        na_dlq,
        duration=15,
        message="mensagem saudável não deveria ir para a DLQ",
    )
