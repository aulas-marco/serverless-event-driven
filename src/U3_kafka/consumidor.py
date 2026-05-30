"""Consumidor Kafka (U3V8). Commit manual → semântica at-least-once."""
import os

from confluent_kafka import Consumer

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")


def criar_consumidor(group_id: str) -> Consumer:
    return Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": group_id,
        "enable.auto.commit": False,       # commit manual: nós controlamos
        "auto.offset.reset": "earliest",   # sem offset commitado → começa do início
    })


def consumir_uma(consumidor: Consumer, timeout: float = 2.0):
    """Faz um poll; retorna a mensagem (ou None se nada chegou / só erro)."""
    msg = consumidor.poll(timeout)
    if msg is None or msg.error():
        return None
    return msg


def processar_com_commit_manual(consumidor: Consumer, handler) -> None:
    """Processa uma mensagem e só commita se o handler NÃO lançar.

    Se o handler lança, o offset não é commitado → a mensagem será reentregue
    (at-least-once). Cabe ao handler ser idempotente.
    """
    msg = consumir_uma(consumidor)
    if msg is None:
        return
    handler(msg)               # se lançar, não chega no commit
    consumidor.commit(msg)     # confirma o processamento
