"""Eventos de domínio da Conta Bancária (U2: Event Sourcing).

Um evento é um fato passado imutável. O estado da conta é derivado
exclusivamente da sequência de eventos — nunca persistido diretamente.
"""
import json
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ContaCriada:
    aggregate_id: str


@dataclass(frozen=True)
class DepositoRealizado:
    aggregate_id: str
    valor: Decimal


@dataclass(frozen=True)
class SaqueRealizado:
    aggregate_id: str
    valor: Decimal


# Mapa tipo->classe para desserialização.
_TIPOS = {
    "ContaCriada": ContaCriada,
    "DepositoRealizado": DepositoRealizado,
    "SaqueRealizado": SaqueRealizado,
}


def item_de_evento(evento, sequencia: int, criado_em: int) -> dict:
    """Converte um evento de domínio num item DynamoDB (append-only)."""
    dados = {k: v for k, v in evento.__dict__.items() if k != "aggregate_id"}
    return {
        "aggregate_id": evento.aggregate_id,
        "sequencia": sequencia,
        "tipo": type(evento).__name__,
        "payload": json.dumps(dados, default=str),
        "criado_em": criado_em,
    }


def evento_de_item(item: dict):
    """Reconstrói o evento de domínio a partir do item DynamoDB."""
    classe = _TIPOS[item["tipo"]]
    dados = json.loads(item["payload"])
    if "valor" in dados:
        dados["valor"] = Decimal(str(dados["valor"]))
    return classe(aggregate_id=item["aggregate_id"], **dados)
