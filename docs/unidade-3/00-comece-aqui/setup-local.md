# Setup local

Neste passo a passo você vai clonar o repositório, instalar as dependências, subir o LocalStack com Kafka e rodar os testes da Unidade 3 — tudo localmente, sem conta AWS e sem chave Anthropic.

---

## 1. Clonar o repositório

```bash
git clone <url-do-repositório>
cd serverless-event-driven
```

---

## 2. Instalar dependências — `make install`

```bash
make install
```

O comando cria o ambiente virtual em `.venv/` e instala `boto3`, `pytest`, `confluent-kafka`, `anthropic` e demais dependências.

Quando terminar você verá algo como:

```
✅  Dependências instaladas em .venv/ — Python 3.x
```

> ⚠️ **Ponto de Atenção**
>
> Você **não precisa** rodar `source .venv/bin/activate` antes de usar os alvos do `make`.
> O Makefile chama `.venv/bin/python3` diretamente — o ambiente virtual já é usado de forma transparente.
> Se preferir ativar o ambiente para rodar scripts manualmente, isso continua funcionando normalmente.

---

## 3. Subir os serviços — `make up`

```bash
make up
```

Esse comando executa `docker compose up -d` e aguarda o LocalStack estar pronto via `infra/scripts/wait-localstack.sh`. O script faz **varredura de saúde** (polling do endpoint `/health`) — não usa `sleep` fixo — então avança assim que o serviço responde.

O `docker compose up` sobe **três serviços** ao mesmo tempo:

| Serviço | Porta | O que é |
|---|---|---|
| `localstack` | 4566 | AWS local (SQS, DynamoDB, Lambda) |
| `kafka` | 9092 | Broker Kafka em modo KRaft (sem ZooKeeper) |
| `kafka-ui` | 8080 | Interface web para inspecionar tópicos e mensagens |

Após o `make up` você pode abrir <http://localhost:8080> para ver o Kafka UI.

---

## 4. Rodar os testes da Unidade 3 — `make test-u3`

```bash
make test-u3
```

Roda os três conjuntos de testes com `pytest tests/ -v -k u3` (ou equivalente configurado no Makefile).

| Alvo | Demo | O que testa |
|---|---|---|
| `make test-u3v7` | Produtor Kafka | Publicação e particionamento por chave |
| `make test-u3v8` | Consumidor Kafka | Commit manual e semântica at-least-once |
| `make test-u3v9` | Classificador com IA | Roteamento, cache DynamoDB, tratamento de erro |

Você também pode rodar cada demo individualmente:

```bash
make test-u3v7
make test-u3v8
make test-u3v9
```

> **Os testes da U3V9 não precisam de chave Anthropic.** O cliente LLM é substituído por um `ClienteFake` que retorna respostas controladas — o pipeline inteiro é exercitado sem nenhuma chamada de rede ao modelo.

---

## 5. Comandos úteis para inspecionar o Kafka

Depois que os serviços sobem, você pode usar o CLI do Kafka dentro do container para explorar o broker:

```bash
# Listar tópicos criados
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list

# Ver detalhes de um tópico (partições, réplicas, líder)
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --describe --topic <nome-do-tópico>
```

Ou acesse o Kafka UI em <http://localhost:8080> para uma visão visual dos tópicos, partições e mensagens.

---

## 6. Inspecionar recursos AWS no LocalStack

```bash
export AWS_ENDPOINT_URL=http://localhost:4566

# Listar filas SQS criadas
aws --endpoint-url=$AWS_ENDPOINT_URL sqs list-queues

# Listar tabelas DynamoDB
aws --endpoint-url=$AWS_ENDPOINT_URL dynamodb list-tables
```

---

## 7. Encerrar — `make clean`

```bash
make clean
```

Para todos os containers (LocalStack, Kafka, Kafka UI) e remove arquivos temporários gerados durante os testes.

---

⬅️ [Anterior: Pré-requisitos](pre-requisitos.md) · 📑 [Índice](../index.md) · [Próximo: Kafka — o log](../01-fundamentos/1-kafka-log-particoes.md) ➡️
