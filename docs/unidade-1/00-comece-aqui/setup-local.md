# Setup local

Neste passo a passo você vai clonar o repositório, instalar as dependências, subir o LocalStack e rodar os três testes de demonstração — tudo localmente, sem conta AWS.

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

O comando cria o ambiente virtual em `.venv/` e instala `boto3`, `pytest` e demais dependências.

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

## 3. Subir o LocalStack — `make up`

```bash
make up
```

Esse comando executa `docker compose up -d` e então aguarda o LocalStack estar pronto via `infra/scripts/wait-localstack.sh`.
O script faz **varredura de saúde** (polling do endpoint `/health`) — não usa `sleep` fixo — então ele avança assim que o serviço responde.

---

## 4. Rodar os testes — `make test`

```bash
make test
```

Roda os três conjuntos de testes com `pytest tests/ -v`.

| Alvo | Demo | Observação |
|---|---|---|
| `make test-u1v7` | Fan-out (SNS → múltiplas filas SQS) | Rápido |
| `make test-u1v8` | Idempotência (escrita condicional) | Rápido |
| `make test-u1v9` | DLQ (ciclos de retry) | **~2 min** — aguarda 3 ciclos de reprocessamento |

Você também pode rodar cada demo individualmente:

```bash
make test-u1v7
make test-u1v8
make test-u1v9
```

---

## 5. Inspecionar os recursos criados

Após os testes você pode explorar o que foi provisionado no LocalStack via AWS CLI:

```bash
export AWS_ENDPOINT_URL=http://localhost:4566

# Listar tópicos SNS criados
aws --endpoint-url=$AWS_ENDPOINT_URL sns list-topics

# Listar filas SQS criadas
aws --endpoint-url=$AWS_ENDPOINT_URL sqs list-queues
```

---

## 6. Encerrar — `make clean`

```bash
make clean
```

Para o LocalStack e remove arquivos temporários gerados durante os testes.

---

⬅️ [Anterior: Pré-requisitos](pre-requisitos.md) · 📑 [Índice](../index.md) · [Próximo: Serverless e Lambda](../01-fundamentos/1-serverless-e-lambda.md) ➡️
