import json
import uuid
import pytest

from tests.aws_builder import FilasEDeCacheU3
from tests.helpers import wait_until
from tests.narracao import narrador
from src.U3_ia import classificador


@pytest.fixture(scope="module", autouse=True)
def _demo_banner():
    narrador.demo(
        "U3V9 — Classificador de eventos com IA",
        "A Lambda classifica o e-mail via LLM, usa cache e roteia para a fila certa.",
    )


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
    narrador.evento("e-mail recebido para classificar", {"texto": "servidor caiu ..."})
    narrador.nota("Classificando via LLM (mock) → prioridade ALTA.")
    classificador.lambda_handler(_evento(f"servidor caiu {uuid.uuid4()}"), None)

    wait_until(lambda: len(infra.receber(sqs, "alta-prioridade")) > 0, timeout=10,
               message="mensagem não chegou em alta-prioridade")
    narrador.consumo("fila alta-prioridade", {"chamadas_ao_llm": fake.chamadas})
    assert fake.chamadas == 1


def test_cache_evita_segunda_chamada_ao_llm(infra, sqs):
    fake = ClienteFake(prioridade="baixa")
    classificador.usar_cliente_llm(fake)
    texto = f"duvida comercial {uuid.uuid4()}"
    narrador.nota("Mesmo texto 2×: a 2ª resolve pelo cache (DynamoDB), sem nova chamada ao LLM.")
    classificador.lambda_handler(_evento(texto), None)
    classificador.lambda_handler(_evento(texto), None)  # mesmo texto
    narrador.observacao("Chamadas ao LLM para 2 invocações idênticas", depois=fake.chamadas)
    assert fake.chamadas == 1  # 2ª resolveu pelo cache


def test_json_invalido_vai_para_sem_classificacao(infra, sqs):
    class FakeInvalido(ClienteFake):
        def __init__(self):
            super().__init__()
            self.messages = type("M", (), {"create": lambda *_a, **_k: type(
                "R", (), {"content": [type("B", (), {"text": "isto não é json"})()]})()})()
    classificador.usar_cliente_llm(FakeInvalido())
    narrador.nota("O LLM devolveu algo que não é JSON → roteia para sem-classificacao.")
    classificador.lambda_handler(_evento(f"texto ruim {uuid.uuid4()}"), None)

    wait_until(lambda: len(infra.receber(sqs, "sem-classificacao")) > 0, timeout=10,
               message="mensagem inválida não foi para sem-classificacao")
    narrador.observacao("Mensagem roteada para a fila sem-classificacao", depois="ok")
