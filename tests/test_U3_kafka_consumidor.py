import json
import uuid
import pytest

from src.U3_kafka.produtor import criar_producer, criar_topico, publicar
from src.U3_kafka.consumidor import criar_consumidor, consumir_uma

# Tópico único por execução: isola o consumidor do backlog acumulado de outros
# testes/execuções (com earliest, um tópico compartilhado faria o consumidor
# replayar centenas de mensagens e estourar o orçamento de polls antes de achar a sua).
TOPICO = f"eventos-suporte-consumidor-{uuid.uuid4()}"


@pytest.fixture(scope="module")
def topico():
    criar_topico(TOPICO, particoes=6)
    return TOPICO


def test_consome_mensagem_publicada(topico):
    chave = f"k-{uuid.uuid4()}"
    publicar(criar_producer(), topico, chave=chave, valor={"sku": "ABC"})

    consumidor = criar_consumidor(group_id=f"g-{uuid.uuid4()}")
    consumidor.subscribe([topico])
    try:
        encontrada = None
        for _ in range(50):
            msg = consumir_uma(consumidor, timeout=2.0)
            if msg and msg.key() == chave.encode():
                encontrada = msg
                break
        assert encontrada is not None
        assert json.loads(encontrada.value())["sku"] == "ABC"
    finally:
        consumidor.close()


def test_at_least_once_sem_commit_rele(topico):
    chave = f"k-{uuid.uuid4()}"
    publicar(criar_producer(), topico, chave=chave, valor={"sku": "XYZ"})
    grupo = f"g-{uuid.uuid4()}"

    def ler_minha_msg():
        c = criar_consumidor(group_id=grupo)
        c.subscribe([TOPICO])
        achou = False
        for _ in range(50):
            msg = consumir_uma(c, timeout=2.0)
            if msg and msg.key() == chave.encode():
                achou = True
                break
        return c, achou

    # 1ª sessão: lê mas NÃO commita → fecha
    c1, achou1 = ler_minha_msg()
    assert achou1
    c1.close()

    # 2ª sessão, mesmo group.id: offset não commitado → relê
    c2, achou2 = ler_minha_msg()
    c2.close()
    assert achou2
