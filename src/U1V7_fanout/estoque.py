"""
Lambda B — Consumidora de Estoque (U1V7: Fan-out)

Consome mensagens da fila-estoque disparadas pelo SNS via fan-out.
Com RawMessageDelivery=true na assinatura, body já é o JSON do pedido.
"""


def lambda_handler(event, context):
    for record in event["Records"]:
        # Com "raw message delivery" ativo, body é o JSON puro do PedidoCriado.
        # Sem ele, o SNS envolve o payload em um envelope com campos Type, MessageId, etc.
        print(f"[ESTOQUE] recebido: {record['body']}")
        # Aqui entraria a reserva de estoque — fora do escopo desta demo.
