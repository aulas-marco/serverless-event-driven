# 1. Serverless e Lambda

## O que é serverless

Serverless não significa "sem servidor" — significa que **você não gerencia o servidor**. O provedor de nuvem (aqui, a AWS) provisiona, escala e desliga a infraestrutura. Você escreve apenas a lógica da sua função; a AWS executa essa função sob demanda, cada vez que um evento chega.

Consequências práticas:
- Não há instância EC2 para configurar, aplicar patch ou monitorar.
- Você paga por invocação e por milissegundo de CPU utilizado — não por servidor ocioso.
- O provedor decide em qual máquina sua função roda; você não tem controle disso.

## O que é uma função Lambda

Uma função Lambda é uma unidade de computação com assinatura padronizada:

```python
def lambda_handler(event, context):
    ...
```

- `event` — dicionário com os dados do gatilho (mensagem SQS, requisição HTTP, etc.).
- `context` — metadados da invocação (tempo restante, ID da requisição, etc.).

Abaixo está o handler do produtor da demo U1V7 — o primeiro código real deste curso:

```python
def lambda_handler(event, context):
    pedido = {
        "pedidoId": str(uuid.uuid4()),
        "clienteId": "cliente-42",
        "valor": "199.90",
        "criadoEm": datetime.now(timezone.utc).isoformat(),
    }
    payload = json.dumps(pedido)

    # UMA publicação. O fan-out (entrega para múltiplas filas) acontece aqui,
    # no SNS, via assinaturas configuradas — não neste código.
    _sns.publish(TopicArn=TOPIC_ARN, Message=payload)

    print(f"[PRODUTOR] Publicado PedidoCriado: {payload}")
    return pedido["pedidoId"]
```

Repare: o handler não sabe quantos consumidores existem. Ele publica um fato — `PedidoCriado` — e delega o restante ao SNS.

## Cold start vs warm: por que clientes boto3 ficam fora do handler

Quando a Lambda recebe tráfego pela primeira vez (ou após um período ocioso), a AWS precisa inicializar o ambiente de execução — carregar o runtime Python, importar módulos, executar o código de nível de módulo. Esse custo extra é chamado de **cold start**.

Nas invocações seguintes, a mesma instância fica "aquecida" (*warm*): o ambiente já existe e a AWS reusa o processo. O código de nível de módulo **não é re-executado** — apenas o corpo do handler é chamado novamente.

Por isso, objetos que custam tempo para criar (conexões TCP, clientes de SDK) devem ser inicializados **fora do handler**:

```python
# Clientes criados fora do handler: reutilizados entre invocações na mesma instância quente.
# AWS_ENDPOINT_URL é lida automaticamente pelo boto3 — aponta para LocalStack ou AWS Real.
_sns = boto3.client("sns", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))

TOPIC_ARN = os.environ["TOPIC_ARN"]  # ARN vem de variável de ambiente — nunca hardcoded
```

Se `_sns` fosse criado dentro do handler, uma nova conexão TCP seria aberta a cada invocação — desperdício de latência e de custo.

> 📌 **Conceito**: termos como *cold start*, *handler*, *ARN* e *endpoint URL* estão definidos no [Glossário](../glossario.md).

---

⬅️ [Anterior: Setup local](../00-comece-aqui/setup-local.md) · 📑 [Índice](../index.md) · [Próximo: Orientado a eventos](2-orientado-a-eventos.md) ➡️
