# Serverless Event-Driven — Demos Educacionais

Projeto de código para as demos das três unidades do curso **IEC EAD — Serverless Computing e Arquiteturas Event-Driven** (PUC Minas / IEC).

> **Portal de documentação:** comece por [docs/index.md](docs/index.md) — hub com as trilhas das três unidades.

Cada demo é executável localmente via LocalStack/Docker ou na AWS Real, **sem nenhuma mudança de código** — apenas variáveis de ambiente.

---

## As três unidades

| Unidade | Tema | Padrões / Demos | Serviços |
|---|---|---|---|
| **U1** | Serverless e Mensageria | U1V7 fan-out · U1V8 idempotência · U1V9 DLQ | SNS · SQS · Lambda · DynamoDB |
| **U2** | Event Sourcing + CQRS | U2V7 event store · U2V8 replay/snapshots · U2V9 projeção CQRS | DynamoDB (event store) · DynamoDB Streams |
| **U3** | Kafka + Programação Reativa + IA | U3V7 produtor · U3V8 consumidor · U3V9 classificador IA | Kafka (KRaft) · asyncio · Lambda + Anthropic |

> **U3 — nota:** Kafka roda local via Docker (sem equivalente AWS neste curso). A chamada à API Anthropic ocorre apenas no Modo AWS Real — os testes locais a mocam.

---

## Portais de documentação

Cada unidade tem trilha própria: `comece-aqui → fundamentos → demos → arquitetura → exercícios → glossário`.

| Portal | Link |
|---|---|
| Hub geral | [docs/index.md](docs/index.md) |
| Unidade 1 — Serverless/Mensageria | [docs/unidade-1/index.md](docs/unidade-1/index.md) |
| Unidade 2 — Event Sourcing + CQRS | [docs/unidade-2/index.md](docs/unidade-2/index.md) |
| Unidade 3 — Kafka + IA | [docs/unidade-3/index.md](docs/unidade-3/index.md) |

---

## Pré-requisitos

| Ferramenta | Versão | Para quê |
|---|---|---|
| Docker | recente | LocalStack + Kafka + Kafka UI |
| Python | 3.12+ | Rodar os testes |
| make | qualquer | Atalhos de comando (pré-instalado no Mac via Xcode CLI Tools) |
| AWS CLI v2 | recente | Inspecionar recursos via terminal |
| SAM CLI | recente | Deploy na AWS Real (opcional) |

> `boto3`, `pytest`, `confluent-kafka` e `anthropic` são instalados via `pip install -r requirements.txt`.

> **Mac:** `make` já vem com o Xcode Command Line Tools. Se não tiver: `xcode-select --install`.

---

## Quick Start (modo local)

```bash
# 1. Clonar e entrar no diretório
git clone <url>
cd serverless-event-driven

# 2. Criar ambiente virtual e instalar dependências
make install

# Ou manualmente:
# python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# 3. Subir LocalStack + Kafka + Kafka UI
make up
# Kafka UI disponível em http://localhost:8080

# 4. Rodar todos os testes
make test

# Ou por unidade:
make test-v7   # U1 — fan-out
make test-v8   # U1 — idempotência
make test-v9   # U1 — DLQ (~2 min — aguarda 3 ciclos de retry)
make test-u2   # U2 — Event Sourcing + CQRS
make test-u3   # U3 — Kafka + IA

# 5. Inspecionar recursos criados (U1/U2 — serviços AWS)
export AWS_ENDPOINT_URL=http://localhost:4566
aws --endpoint-url=$AWS_ENDPOINT_URL sns list-topics
aws --endpoint-url=$AWS_ENDPOINT_URL sqs list-queues

# 6. Limpar
make clean
```

> Sempre ative o ambiente virtual antes de rodar os testes (`source .venv/bin/activate`). O prompt mostrará `(.venv)` quando ativo.

---

## Estrutura do projeto

```
serverless-event-driven/
├── src/
│   ├── U1V7_fanout/              # Fan-out SNS → SQS → Lambda
│   ├── U1V8_idempotencia/        # Escrita condicional DynamoDB
│   ├── U1V9_dlq/                 # Falha proposital → ciclo DLQ
│   ├── U2_event_sourcing/        # Event store, replay, snapshots, CQRS
│   ├── U3_kafka/                 # Produtor e consumidor Kafka (asyncio)
│   └── U3_ia/                    # Classificador IA — Lambda + Anthropic
├── infra/
│   ├── template.yaml             # Modelo SAM — infraestrutura como código
│   └── scripts/
│       ├── setup.sh
│       ├── teardown.sh
│       ├── wait-localstack.sh
│       └── wait-kafka.sh
├── tests/
│   ├── helpers.py                # esperar_até, implantar_lambda, criar_cliente
│   ├── aws_builder.py            # Padrão de infraestrutura educacional
│   ├── conftest.py               # Fixtures de sessão
│   ├── test_U1V7_fanout.py
│   ├── test_U1V8_idempotencia.py
│   ├── test_U1V9_dlq.py
│   ├── test_U2_event_store.py
│   ├── test_U2_replay_snapshots.py
│   ├── test_U2_cqrs_projecao.py
│   ├── test_U3_kafka_produtor.py
│   ├── test_U3_kafka_consumidor.py
│   └── test_U3_ia_classificador.py
└── docs/
    ├── index.md                  # Hub — portal de documentação geral
    ├── unidade-1/                # Trilha U1 (comece-aqui / fundamentos / demos / arquitetura)
    ├── unidade-2/                # Trilha U2
    └── unidade-3/                # Trilha U3
```

---

## Modo AWS Real

```bash
# Remover variável de endpoint e usar credenciais reais
unset AWS_ENDPOINT_URL
aws configure  # ou exportar AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY

# Deploy via SAM
make deploy-aws
```

> Na U3, Kafka continua rodando via Docker local (não há equivalente AWS gerenciado neste ambiente). A chamada Anthropic passa a ser real — certifique-se de ter `ANTHROPIC_API_KEY` exportado.

---

## Padrões adotados

### `esperar_até` em vez de `time.sleep`

Todos os testes usam varredura com tempo limite. Nunca suspensão fixa.

```python
# Correto — espera até a condição ser verdadeira (ou tempo limite)
esperar_até(lambda: mensagem_na_fmm(), timeout=90)

# Evitar — suspensão fixa torna o teste lento OU frágil
time.sleep(30)
```

### `endpoint_url=os.environ.get("AWS_ENDPOINT_URL")`

Todos os clientes boto3 leem `AWS_ENDPOINT_URL`. Quando não definida, `endpoint_url=None` é ignorado pelo boto3 — o cliente usa a AWS real. Zero mudança de código entre modos.

### Infraestrutura como código

Toda a topologia AWS está declarada em `infra/template.yaml`. A distribuição em leque, a DLQ (RedrivePolicy) e o TTL (TimeToLiveSpecification) estão visíveis como código, não como cliques no console.

---

## Comandos disponíveis

```
make help
```

---

## Referências

- [Hub de documentação](docs/index.md)
- [Portal Unidade 1 — Serverless/Mensageria](docs/unidade-1/index.md)
- [Portal Unidade 2 — Event Sourcing + CQRS](docs/unidade-2/index.md)
- [Portal Unidade 3 — Kafka + IA](docs/unidade-3/index.md)
