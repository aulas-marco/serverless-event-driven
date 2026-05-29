"""
Fixtures compartilhadas entre todos os testes.

Escopo 'session': os clientes boto3 e os recursos AWS são criados
uma única vez para toda a execução do pytest.

Pré-condição: LocalStack deve estar rodando.
Execute `make up` antes de `make test`.
"""
import json
import os

import pytest

from tests.helpers import make_client, make_resource, wait_until

ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")


@pytest.fixture(scope="session", autouse=True)
def localstack_health():
    """Verifica que o LocalStack está respondendo antes de qualquer teste."""
    import urllib.request
    import urllib.error

    def health_ok():
        try:
            with urllib.request.urlopen(f"{ENDPOINT}/_localstack/health", timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    wait_until(health_ok, timeout=30, message="LocalStack não está respondendo. Execute `make up`.")


@pytest.fixture(scope="session")
def sns():
    return make_client("sns")


@pytest.fixture(scope="session")
def sqs():
    return make_client("sqs")


@pytest.fixture(scope="session")
def dynamodb():
    return make_client("dynamodb")


@pytest.fixture(scope="session")
def lam():
    """Cliente Lambda (evita conflito com builtin 'lambda')."""
    return make_client("lambda")


@pytest.fixture(scope="session")
def dynamodb_resource():
    return make_resource("dynamodb")
