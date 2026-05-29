from __future__ import annotations  # habilita dict | None em Python 3.9

"""
Utilitários compartilhados entre os testes.

Padrões adotados do projeto aspire-aws:
- wait_until: polling com timeout em vez de time.sleep fixo
- deploy_lambda: empacota e sobe um handler .py no LocalStack
"""
import io
import os
import time
import zipfile
from pathlib import Path
from typing import Callable


ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
IAM_ROLE = "arn:aws:iam::000000000000:role/local-role"  # papel fictício aceito pelo LocalStack


def make_client(service: str, boto3_session=None):
    """Cria um cliente boto3 apontando para LocalStack ou AWS Real."""
    import boto3
    session = boto3_session or boto3
    kwargs = dict(region_name=REGION, endpoint_url=ENDPOINT)
    if ENDPOINT.startswith("http://localhost"):
        kwargs["aws_access_key_id"] = "test"
        kwargs["aws_secret_access_key"] = "test"
    return session.client(service, **kwargs)


def make_resource(service: str):
    """Cria um recurso boto3 (ex: dynamodb) apontando para LocalStack ou AWS Real."""
    import boto3
    kwargs = dict(region_name=REGION, endpoint_url=ENDPOINT)
    if ENDPOINT.startswith("http://localhost"):
        kwargs["aws_access_key_id"] = "test"
        kwargs["aws_secret_access_key"] = "test"
    return boto3.resource(service, **kwargs)


# ── Polling helper ────────────────────────────────────────────────────────────

def drain_queue(sqs_client, queue_url: str) -> int:
    """
    Remove todas as mensagens pendentes de uma fila SQS.
    Garante isolamento entre execuções de teste — sem mensagens antigas
    que causariam falsos negativos em receive_message com MaxNumberOfMessages=1.
    Retorna o número de mensagens removidas.
    """
    removidas = 0
    while True:
        resp = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            VisibilityTimeout=1,
        )
        msgs = resp.get("Messages", [])
        if not msgs:
            break
        for m in msgs:
            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=m["ReceiptHandle"],
            )
        removidas += len(msgs)
    return removidas


def wait_until(
    condition: Callable[[], bool],
    timeout: float = 30.0,
    interval: float = 0.5,
    message: str = "condição não satisfeita no tempo esperado",
) -> None:
    """
    Aguarda até que condition() retorne True.
    Lança TimeoutError se o timeout for atingido.

    Nunca use time.sleep fixo nos testes — use wait_until.
    Isso evita testes lentos quando o sistema responde rápido
    e falsos positivos quando está lento.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(interval)
    raise TimeoutError(f"wait_until: {message} (timeout={timeout}s)")


def assert_never(
    condition: Callable[[], bool],
    duration: float = 5.0,
    interval: float = 0.5,
    message: str = "condição não deveria ser verdadeira",
) -> None:
    """
    Verifica que condition() NÃO se torna True durante 'duration' segundos.
    Útil para asserções negativas: "esta mensagem não deveria chegar".
    """
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        if condition():
            raise AssertionError(f"assert_never: {message}")
        time.sleep(interval)


# ── Lambda deployment ─────────────────────────────────────────────────────────

def deploy_lambda(
    lambda_client,
    function_name: str,
    source_path: str,
    handler: str,
    env_vars: dict | None = None,
) -> None:
    """
    Empacota um arquivo .py como ZIP e cria (ou atualiza) a função Lambda no LocalStack.

    Args:
        lambda_client: cliente boto3 do Lambda
        function_name: nome da função Lambda
        source_path: caminho para o arquivo .py (ex: src/U1V7_fanout/produtor.py)
        handler: módulo.função (ex: produtor.lambda_handler)
        env_vars: variáveis de ambiente injetadas na função
    """
    source = Path(source_path)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(source, arcname=source.name)
    zip_buffer.seek(0)

    kwargs = dict(
        FunctionName=function_name,
        Runtime="python3.12",
        Role=IAM_ROLE,
        Handler=handler,
        Code={"ZipFile": zip_buffer.read()},
        Timeout=30,
        Environment={"Variables": env_vars or {}},
    )

    try:
        lambda_client.create_function(**kwargs)
    except lambda_client.exceptions.ResourceConflictException:
        # Função já existe — atualizar código
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=kwargs["Code"]["ZipFile"],
        )

    # Aguarda a função ficar Active antes de invocar
    wait_until(
        lambda: lambda_client.get_function(FunctionName=function_name)
        ["Configuration"]["State"] == "Active",
        timeout=30,
        message=f"Lambda '{function_name}' não ficou Active",
    )
