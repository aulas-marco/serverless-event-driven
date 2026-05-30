"""Agregado ContaBancaria (U2). O saldo é o fold da sequência de eventos."""
from decimal import Decimal

from src.U2_event_sourcing.eventos import (
    ContaCriada, DepositoRealizado, SaqueRealizado,
)


class ContaBancaria:
    def __init__(self):
        self.existe = False
        self.saldo = Decimal("0")

    @classmethod
    def reconstruir(cls, eventos: list) -> "ContaBancaria":
        conta = cls()
        for evento in eventos:
            conta.aplicar(evento)
        return conta

    def aplicar(self, evento) -> None:
        if isinstance(evento, ContaCriada):
            self.existe = True
        elif isinstance(evento, DepositoRealizado):
            self.saldo += evento.valor
        elif isinstance(evento, SaqueRealizado):
            self.saldo -= evento.valor
