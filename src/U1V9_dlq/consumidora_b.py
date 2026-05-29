"""
Lambda B — Consumidora de Estoque com DLQ (U1V9)

Consome mensagens da fila-estoque. Rejeita mensagens com flag "defeituoso"
lançando uma exceção que escapa do handler — isso sinaliza ao SQS que
a mensagem NÃO foi processada e não deve ser deletada.

Após maxReceiveCount recepções com falha, o SQS roteia a mensagem para a DLQ.

Para demonstrar o fluxo de correção:
  1. Enviar mensagem com "defeituoso": true  → vai para DLQ após 3 tentativas
  2. Corrigir o código (remover a exceção)    → redeploy
  3. Reenviar da DLQ para a fila principal   → processa com sucesso
"""
import json


def lambda_handler(event, context):
    for record in event["Records"]:
        body = record["body"]
        print(f"[CONSUMIDORA-B] Processando: {body}")

        pedido = json.loads(body)

        # FALHA PROPOSITAL — presente apenas para demonstração do ciclo DLQ.
        # Para demonstrar a correção (Passo 7 do roteiro), remova este bloco.
        if pedido.get("defeituoso"):
            raise RuntimeError(
                f"[CONSUMIDORA-B] Falha: payload defeituoso detectado — {pedido.get('sku')}"
            )

        # Lógica normal de baixa de estoque (idempotente via U1V8).
        print(f"[CONSUMIDORA-B] Estoque baixado para SKU: {pedido.get('sku')}")
