from decimal import Decimal

from src.U2_event_sourcing.eventos import (
    ContaCriada, DepositoRealizado, SaqueRealizado, evento_de_item, item_de_evento,
)


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
