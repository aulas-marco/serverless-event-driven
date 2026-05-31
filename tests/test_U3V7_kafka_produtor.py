import uuid
import pytest

from src.U3_kafka.produtor import criar_producer, criar_topico, publicar
from tests.narracao import narrador

TOPICO = "eventos-suporte"


@pytest.fixture(scope="module", autouse=True)
def _demo_banner():
    narrador.demo(
        "U3V7 — Produtor Kafka (particionamento por chave)",
        "A chave da mensagem decide a partição; mesma chave → mesma partição.",
    )


@pytest.fixture(scope="module")
def topico():
    criar_topico(TOPICO, particoes=6)
    narrador.recurso("tópico Kafka", TOPICO, particoes="6")
    return TOPICO


def test_mesma_chave_cai_sempre_na_mesma_particao(topico):
    p = criar_producer()
    narrador.evento("5 publicações com a MESMA chave 'cliente-1'", {"chave": "cliente-1", "n": 5})
    particoes = {publicar(p, topico, chave="cliente-1", valor={"i": i}) for i in range(5)}
    narrador.observacao("Todas caíram na mesma partição", depois=sorted(particoes))
    assert len(particoes) == 1  # mesma chave → uma única partição


def test_sem_chave_distribui_entre_particoes(topico):
    p = criar_producer()
    narrador.evento("30 publicações SEM chave", {"chave": None, "n": 30})
    particoes = {publicar(p, topico, chave=None, valor={"i": i}) for i in range(30)}
    narrador.observacao("Distribuídas entre várias partições", depois=len(particoes))
    assert len(particoes) >= 2  # sem chave → round-robin/aleatório espalha
