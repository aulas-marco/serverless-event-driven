"""Handlers de comando da Conta Bancária (U2). Comandos só ANEXAM eventos."""
from decimal import Decimal

from src.U2_event_sourcing.conta import ContaBancaria
from src.U2_event_sourcing.eventos import (
    ContaCriada, DepositoRealizado, SaqueRealizado,
)


class SaldoInsuficiente(Exception):
    """Levantada quando um saque excede o saldo reconstruído."""


def _garantir_conta(store, conta_id: str) -> ContaBancaria:
    eventos = store.carregar_por_agregado(conta_id)
    conta = ContaBancaria.reconstruir(eventos)
    if not conta.existe:
        store.append(conta_id, ContaCriada(aggregate_id=conta_id))
    return conta


def depositar(store, conta_id: str, valor: Decimal) -> None:
    _garantir_conta(store, conta_id)
    store.append(conta_id, DepositoRealizado(aggregate_id=conta_id, valor=valor))


def sacar(store, conta_id: str, valor: Decimal) -> None:
    conta = ContaBancaria.reconstruir(store.carregar_por_agregado(conta_id))
    if valor > conta.saldo:
        raise SaldoInsuficiente(
            f"Saque de {valor} excede o saldo de {conta.saldo} (conta {conta_id})"
        )
    store.append(conta_id, SaqueRealizado(aggregate_id=conta_id, valor=valor))
