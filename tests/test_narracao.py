"""
Testes do Narrador didático.

Verificam o contrato essencial: DESLIGADO não imprime nada (no-op);
LIGADO imprime banner, passos numerados e payloads identados.
Testam a classe Narrador diretamente (não o singleton de módulo), para
controlar a env via monkeypatch sem depender da ordem de import.
"""
from tests.narracao import Narrador


def test_desligado_nao_imprime_nada(capsys, monkeypatch):
    monkeypatch.delenv("NARRAR", raising=False)
    n = Narrador()
    n.demo("Titulo", "Resumo")
    n.recurso("tópico SNS", "pedidos", arn="arn:aws:sns:...")
    n.evento("PedidoCriado", {"pedidoId": "P-1"})
    n.entrega("fila-estoque", {"pedidoId": "P-1"})
    n.consumo("Lambda X", {"ok": True})
    n.observacao("saldo mudou", antes=0, depois=100)
    n.nota("comentário")
    assert capsys.readouterr().out == ""


def test_ligado_imprime_banner_passos_e_payload(capsys, monkeypatch):
    monkeypatch.setenv("NARRAR", "1")
    n = Narrador()
    n.demo("U1V7 — Fan-out", "1 publish → 2 filas")
    n.recurso("tópico SNS", "pedidos", arn="arn:aws:sns:abc")
    n.evento("PedidoCriado", {"pedidoId": "P-1"})
    n.observacao("entregue", depois="P-1")
    saida = capsys.readouterr().out

    assert "🎬" in saida                 # banner
    assert "U1V7 — Fan-out" in saida
    assert "1. 📦" in saida              # primeiro passo numerado
    assert "2. ➡️" in saida              # segundo passo
    assert "3. 👀" in saida              # terceiro passo
    assert '"pedidoId": "P-1"' in saida  # payload JSON identado
    assert "arn:aws:sns:abc" in saida    # atributo do recurso


def test_demo_reseta_contador_de_passos(capsys, monkeypatch):
    monkeypatch.setenv("NARRAR", "1")
    n = Narrador()
    n.demo("A", "primeira")
    n.evento("E1", {"x": 1})   # passo 1
    n.demo("B", "segunda")     # reseta
    n.evento("E2", {"x": 2})   # passo 1 de novo
    saida = capsys.readouterr().out
    assert saida.count("1. ➡️") == 2


def test_observacao_formata_antes_depois(capsys, monkeypatch):
    monkeypatch.setenv("NARRAR", "1")
    n = Narrador()
    n.demo("D", "r")
    n.observacao("saldo projetado", antes=0, depois=80)
    saida = capsys.readouterr().out
    assert "0 → 80" in saida


def test_observacao_so_depois_nao_mostra_none(capsys, monkeypatch):
    monkeypatch.setenv("NARRAR", "1")
    n = Narrador()
    n.demo("D", "r")
    n.observacao("entregue", depois="P-1")
    saida = capsys.readouterr().out
    assert "entregue: P-1" in saida
    assert "None" not in saida
