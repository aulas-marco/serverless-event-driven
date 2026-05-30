"""Produtor Kafka (U3V7). Publica eventos; a chave decide a partição."""
import json
import os

from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")


def criar_producer() -> Producer:
    return Producer({"bootstrap.servers": BOOTSTRAP})


def criar_topico(nome: str, particoes: int, bootstrap: str | None = None) -> None:
    admin = AdminClient({"bootstrap.servers": bootstrap or BOOTSTRAP})
    futuros = admin.create_topics([NewTopic(nome, num_partitions=particoes, replication_factor=1)])
    for _, futuro in futuros.items():
        try:
            futuro.result()
        except Exception as e:  # tópico já existe → ok em execuções repetidas
            if "already exists" not in str(e).lower():
                raise


def publicar(producer: Producer, topico: str, chave: str | None, valor: dict) -> int:
    """Publica uma mensagem e retorna a partição em que ela caiu (via delivery report)."""
    particoes: list[int] = []

    def _entrega(err, msg):
        if err is None:
            particoes.append(msg.partition())

    producer.produce(
        topico,
        key=chave.encode() if chave else None,
        value=json.dumps(valor).encode(),
        on_delivery=_entrega,
    )
    producer.flush(10)
    return particoes[0]
