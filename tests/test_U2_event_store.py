from decimal import Decimal

from src.U2_event_sourcing.eventos import (
    ContaCriada, DepositoRealizado, SaqueRealizado, evento_de_item, item_de_evento,
)
from src.U2_event_sourcing.conta import ContaBancaria


def test_evento_serializa_e_desserializa_preservando_tipo_e_dados():
    evento = DepositoRealizado(aggregate_id="conta-1", valor=Decimal("100.50"))
    item = item_de_evento(evento, sequencia=1, criado_em=1717000000)

    assert item["aggregate_id"] == "conta-1"
    assert item["sequencia"] == 1
    assert item["tipo"] == "DepositoRealizado"

    reconstruido = evento_de_item(item)
    assert isinstance(reconstruido, DepositoRealizado)
    assert reconstruido.valor == Decimal("100.50")
    assert reconstruido.aggregate_id == "conta-1"


def test_reconstruir_faz_fold_dos_eventos_ate_o_saldo():
    eventos = [
        ContaCriada(aggregate_id="conta-1"),
        DepositoRealizado(aggregate_id="conta-1", valor=Decimal("100")),
        SaqueRealizado(aggregate_id="conta-1", valor=Decimal("30")),
    ]
    conta = ContaBancaria.reconstruir(eventos)
    assert conta.existe is True
    assert conta.saldo == Decimal("70")


def test_conta_sem_eventos_nao_existe():
    conta = ContaBancaria.reconstruir([])
    assert conta.existe is False
    assert conta.saldo == Decimal("0")
