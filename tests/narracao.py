"""
Narrador didático do curso.

Liga-se via variável de ambiente NARRAR (ex.: `NARRAR=1`, como em
`make narrar-u1v7`). DESLIGADO, é no-op: todos os métodos retornam sem
imprimir nada — os `make test-*` continuam silenciosos e rápidos.

A narração vive SOMENTE na camada de testes (builders + arquivos de teste).
src/ permanece intacto: lá ficam os handlers "de produção".

ATENÇÃO ao chamar os métodos: os argumentos são avaliados mesmo com a
narração desligada. Passe apenas valores baratos / já calculados. Para
computar algo só-para-narrar, proteja com `if narrador.ativo:`.
"""
import json
import os
import sys


class Narrador:
    def __init__(self) -> None:
        self.ativo = bool(os.environ.get("NARRAR"))
        self._passo = 0

    def demo(self, titulo: str, resumo: str) -> None:
        if not self.ativo:
            return
        self._passo = 0
        linha = "━" * 70
        print(f"\n{linha}", file=sys.stdout)
        print(f"  🎬  {titulo}", file=sys.stdout)
        print(f"      {resumo}", file=sys.stdout)
        print(linha, file=sys.stdout)

    def recurso(self, tipo: str, nome: str, **atributos) -> None:
        if not self.ativo:
            return
        self._linha_passo("📦", f"Instanciando {tipo}: {nome}")
        for chave, valor in atributos.items():
            print(f"          {chave} = {valor}", file=sys.stdout)

    def evento(self, nome: str, payload: dict) -> None:
        if not self.ativo:
            return
        self._linha_passo("➡️", f"Evento {nome}")
        self._payload(payload)

    def entrega(self, destino: str, payload) -> None:
        if not self.ativo:
            return
        self._linha_passo("📨", f"Entregue em {destino}")
        self._payload(payload)

    def consumo(self, quem: str, payload) -> None:
        if not self.ativo:
            return
        self._linha_passo("✅", f"Consumido por {quem}")
        self._payload(payload)

    def observacao(self, texto: str, antes=None, depois=None) -> None:
        if not self.ativo:
            return
        if antes is not None or depois is not None:
            texto = f"{texto}: {antes} → {depois}"
        self._linha_passo("👀", texto)

    def nota(self, texto: str) -> None:
        if not self.ativo:
            return
        print(f"      💡  {texto}", file=sys.stdout)

    # ── privados ──
    def _linha_passo(self, simbolo: str, texto: str) -> None:
        self._passo += 1
        print(f"  {self._passo}. {simbolo}  {texto}", file=sys.stdout)

    def _payload(self, payload) -> None:
        if isinstance(payload, dict):
            corpo = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
        else:
            corpo = str(payload)
        for linha in corpo.splitlines():
            print(f"          {linha}", file=sys.stdout)


narrador = Narrador()
