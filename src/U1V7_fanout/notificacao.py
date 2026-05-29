"""
Lambda C — Consumidora de Notificação (U1V7: Fan-out)

Consome mensagens da fila-notificacao disparadas pelo SNS via fan-out.
Estrutura idêntica à Lambda de Estoque — só o domínio muda.
Essa simetria demonstra o desacoplamento: duas reações ao mesmo fato,
escritas e implantadas de forma completamente independente.
"""


def lambda_handler(event, context):
    for record in event["Records"]:
        print(f"[NOTIFICACAO] recebido: {record['body']}")
        # Aqui entraria o envio de e-mail/push — fora do escopo desta demo.
