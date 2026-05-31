import json
import uuid
import pytest

from tests.aws_builder import FilasEDeCacheU3
from tests.helpers import wait_until
from src.U3_ia import classificador


class FakeMensagens:
    def __init__(self, pai):
        self._pai = pai

    def create(self, **kwargs):
        self._pai.chamadas += 1
        texto = json.dumps({"prioridade": self._pai.prioridade, "categoria": "tecnico"})
        return type("Resp", (), {"content": [type("Bloco", (), {"text": texto})()]})()


class ClienteFake:
    """Imita anthropic.Anthropic(): .messages.create(...).content[0].text é JSON."""
    def __init__(self, prioridade="alta"):
        self.prioridade = prioridade
        self.chamadas = 0
        self.messages = FakeMensagens(self)


@pytest.fixture(scope="module")
def infra(sqs, dynamodb_resource):
    return FilasEDeCacheU3(sqs, dynamodb_resource)


@pytest.fixture(autouse=True)
def _reset_override():
    classificador.usar_cliente_llm(None)
    yield
    classificador.usar_cliente_llm(None)


def _evento(texto: str) -> dict:
    return {"Records": [{"body": texto}]}


def test_classifica_e_roteia_para_alta_prioridade(infra, sqs):
    fake = ClienteFake(prioridade="alta")
    classificador.usar_cliente_llm(fake)
    classificador.lambda_handler(_evento(f"servidor caiu {uuid.uuid4()}"), None)

    wait_until(lambda: len(infra.receber(sqs, "alta-prioridade")) > 0, timeout=10,
               message="mensagem não chegou em alta-prioridade")
    assert fake.chamadas == 1


def test_cache_evita_segunda_chamada_ao_llm(infra, sqs):
    fake = ClienteFake(prioridade="baixa")
    classificador.usar_cliente_llm(fake)
    texto = f"duvida comercial {uuid.uuid4()}"
    classificador.lambda_handler(_evento(texto), None)
    classificador.lambda_handler(_evento(texto), None)  # mesmo texto
    assert fake.chamadas == 1  # 2ª resolveu pelo cache


def test_json_invalido_vai_para_sem_classificacao(infra, sqs):
    class FakeInvalido(ClienteFake):
        def __init__(self):
            super().__init__()
            self.messages = type("M", (), {"create": lambda *_a, **_k: type(
                "R", (), {"content": [type("B", (), {"text": "isto não é json"})()]})()})()
    classificador.usar_cliente_llm(FakeInvalido())
    classificador.lambda_handler(_evento(f"texto ruim {uuid.uuid4()}"), None)

    wait_until(lambda: len(infra.receber(sqs, "sem-classificacao")) > 0, timeout=10,
               message="mensagem inválida não foi para sem-classificacao")
