import uuid
import pytest

from src.U3_kafka.produtor import criar_producer, criar_topico, publicar

TOPICO = "eventos-suporte"


@pytest.fixture(scope="module")
def topico():
    criar_topico(TOPICO, particoes=6)
    return TOPICO


def test_mesma_chave_cai_sempre_na_mesma_particao(topico):
    p = criar_producer()
    particoes = {publicar(p, topico, chave="cliente-1", valor={"i": i}) for i in range(5)}
    assert len(particoes) == 1  # mesma chave → uma única partição


def test_sem_chave_distribui_entre_particoes(topico):
    p = criar_producer()
    particoes = {publicar(p, topico, chave=None, valor={"i": i}) for i in range(30)}
    assert len(particoes) >= 2  # sem chave → round-robin/aleatório espalha
