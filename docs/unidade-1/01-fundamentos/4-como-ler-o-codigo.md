# Como Ler o Código

Antes de entrar nas demos, vale saber onde cada peça mora no repositório. Esta página é um mapa rápido para você não se perder.

---

## Estrutura do projeto

```
serverless-event-driven/
├── src/
│   ├── U1V7_fanout/           # Gerenciadores da demo distribuição em leque
│   │   ├── produtor.py        # Lambda A — publica no SNS
│   │   ├── estoque.py         # Lambda B — consome fila-estoque
│   │   └── notificacao.py     # Lambda C — consome fila-notificacao
│   ├── U1V8_idempotencia/
│   │   └── processa_pedido.py # Escrita condicional (idempotência)
│   └── U1V9_dlq/
│       └── consumidora_b.py   # Falha proposital → ciclo DLQ
├── infra/
│   ├── template.yaml          # Modelo SAM — infraestrutura como código
│   └── scripts/
│       ├── setup.sh           # Provisiona recursos no LocalStack
│       ├── teardown.sh        # Remove recursos
│       └── wait-localstack.sh # Verificação de saúde (varredura, nunca suspensão)
├── tests/
│   ├── helpers.py             # wait_until, deploy_lambda, make_client
│   ├── conftest.py            # Acessórios de sessão
│   ├── test_U1V7_fanout.py
│   ├── test_U1V8_idempotencia.py
│   └── test_U1V9_dlq.py
└── docs/
    ├── architecture/
    │   ├── README.md          # Diagramas Mermaid (C4, gráfico de fluxo, sequência)
    │   └── adrs/              # Decisões arquiteturais (ADR-001 a ADR-003)
    └── roteiros/              # Guias passo a passo por demonstração
```

---

## O padrão `endpoint_url=os.environ.get("AWS_ENDPOINT_URL")`

Todos os clientes boto3 do projeto são criados com esta linha (exemplo extraído de `src/U1V7_fanout/produtor.py`):

```python
_sns = boto3.client("sns", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
```

O comportamento é simples:

- **Variável definida** (ex.: `AWS_ENDPOINT_URL=http://localhost:4566`) → boto3 direciona as chamadas para o LocalStack.
- **Variável ausente** → `endpoint_url=None`, que o boto3 simplesmente ignora → as chamadas vão para a AWS real.

Resultado: **zero mudança de código** entre os dois modos. Você troca o ambiente apenas com variáveis de ambiente.

---

## LocalStack ↔ AWS Real

A mesma stack roda nos dois ambientes porque toda a topologia é declarada como código — não há cliques no console que precisem ser repetidos. As decisões técnicas que tornam isso possível estão documentadas nos ADRs:

- **ADR-002** — por que LocalStack foi escolhido para os testes locais.
- **ADR-003** — a convenção `endpoint_url` e por que ela é preferível a mocks.

Você pode ler os dois em [`../03-arquitetura/decisoes-adr.md`](../03-arquitetura/decisoes-adr.md).

---

## Onde a infra mora

Existem dois lugares onde a infraestrutura está definida:

| Arquivo | Propósito |
|---|---|
| `infra/template.yaml` | Modelo SAM — declara todos os recursos (tópico [SNS](../glossario.md#sns), filas [SQS](../glossario.md#sqs), funções Lambda, [ESMs](../glossario.md#esm), [DLQ](../glossario.md#dlq), [TTL](../glossario.md#ttl)). Usado para deploy na AWS Real. |
| `tests/aws_builder.py` | Constrói os mesmos recursos programaticamente via boto3 para os testes de integração. |

O `aws_builder.py` é descrito em detalhes em [`../03-arquitetura/aws-builder.md`](../03-arquitetura/aws-builder.md).

> 💡 **Dica**
>
> Ao ler cada demo, abra o arquivo `src/` correspondente ao lado — o portal mostra o mesmo código que está sendo explicado. Navegar entre a explicação e o código-fonte é a forma mais rápida de consolidar o entendimento.

---

⬅️ [Anterior: Os Quatro Serviços](3-os-quatro-servicos.md) · 📑 [Índice](../index.md) · [Próximo: U1V7 — Fan-out](../02-demos/u1v7-fan-out.md) ➡️
