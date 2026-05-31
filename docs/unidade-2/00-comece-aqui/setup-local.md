# Setup local — Unidade 2

Neste passo a passo você vai clonar o repositório, instalar as dependências, subir o LocalStack com DynamoDB Streams habilitado e rodar os testes da Unidade 2 — tudo localmente, sem conta AWS.

---

## 1. Clonar o repositório

```bash
git clone <url-do-repositório>
cd serverless-event-driven
```

Se você já concluiu a Unidade 1, o repositório já está clonado — pule para o passo 2.

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

**Serviços usados na Unidade 2:**

| Serviço | Para quê |
|---|---|
| DynamoDB | Tabelas `eventos` (com Streams), `saldo_atual` e `snapshots` |
| Lambda | Lambda de projeção `projecao-saldo` acionada pelo stream da tabela `eventos` |

---

## 4. Rodar os testes da Unidade 2 — `make test-u2`

```bash
make test-u2
```

Roda os três conjuntos de testes da U2 com `pytest tests/test_U2_*.py -v`.

| Alvo | Demo | O que cobre |
|---|---|---|
| `make test-u2` | Todos os testes da U2 | Event store, replay/snapshots e projeção via Streams |
| `make test-v7` (U2V7) | Event Store | Comandos `depositar` e `sacar`; append-only; replay de saldo |
| `make test-v8` (U2V8) | Replay e Snapshots | Idempotência do replay; gravação e uso de snapshots |
| `make test-v9` (U2V9) | CQRS e Projeção | Propagação via DynamoDB Streams; consistência eventual; `transferir` atômico |

> **Sobre o tempo de execução:** o teste de projeção (`test_U2_cqrs_projecao.py`) usa `wait_until` com timeout de 60 segundos para aguardar a propagação assíncrona do DynamoDB Streams. Esse comportamento é esperado — não é lentidão, é o mecanismo de consistência eventual sendo demonstrado.

---

## 5. Inspecionar as tabelas criadas

Após os testes você pode explorar o que foi provisionado no LocalStack via AWS CLI:

```bash
# Listar tabelas DynamoDB criadas
aws --endpoint-url=http://localhost:4566 dynamodb list-tables

# Ver os eventos gravados na tabela de Event Store
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name eventos

# Ver o saldo projetado (modelo de leitura do CQRS)
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name saldo_atual

# Ver os snapshots gravados
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name snapshots
```

---

## 6. Encerrar — `make clean`

```bash
make clean
```

Para o LocalStack e remove arquivos temporários gerados durante os testes.

---

⬅️ [Anterior: Pré-requisitos](pre-requisitos.md) · 📑 [Índice](../index.md) · [Próximo: Event Sourcing](../01-fundamentos/1-event-sourcing.md) ➡️
