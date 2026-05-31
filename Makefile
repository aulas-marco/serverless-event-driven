.PHONY: up down setup test \
        test-u1 test-u1v7 test-u1v8 test-u1v9 \
        test-u2 test-u2v7 test-u2v8 test-u2v9 \
        test-u3 test-u3v7 test-u3v8 test-u3v9 \
        clean lint help

VENV    := .venv
PYTHON  := $(VENV)/bin/python3
PYTEST  := $(PYTHON) -m pytest
AWS     := aws --endpoint-url=$(or $(AWS_ENDPOINT_URL),http://localhost:4566) --region=$(or $(AWS_DEFAULT_REGION),us-east-1)

# ── Ambiente ──────────────────────────────────────────────────────────────────

up:  ## Sobe LocalStack + Kafka e aguarda estarem prontos
	docker compose up -d
	@bash infra/scripts/wait-localstack.sh
	@bash infra/scripts/wait-kafka.sh

down:  ## Para e remove o container LocalStack
	docker compose down

setup: up  ## Cria todos os recursos AWS (SNS, SQS, DynamoDB) no LocalStack
	@export AWS_ENDPOINT_URL=$${AWS_ENDPOINT_URL:-http://localhost:4566} && \
	 export AWS_DEFAULT_REGION=$${AWS_DEFAULT_REGION:-us-east-1} && \
	 export AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} && \
	 export AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test} && \
	 bash infra/scripts/setup.sh

teardown:  ## Remove os recursos criados pelo setup
	@bash infra/scripts/teardown.sh

# ── Dependências ──────────────────────────────────────────────────────────────

install:  ## Cria o ambiente virtual com Python 3.13 e instala dependências
	$(or $(shell which python3.13 2>/dev/null),$(shell which python3)) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip -q
	$(VENV)/bin/pip install -r requirements.txt -q
	@echo ""
	@echo "✅  Dependências instaladas em $(VENV)/ — $$($(VENV)/bin/python3 --version)"

# ── Testes ────────────────────────────────────────────────────────────────────

_check-venv:
	@test -f $(VENV)/bin/python3 || (echo "❌  Ambiente virtual não encontrado. Execute: make install" && exit 1)

# Prefixo de variáveis de ambiente que apontam os testes ao LocalStack
# (todas sobrescrevíveis pelo shell). Aplicado inline a cada invocação do pytest.
AWS_TEST_ENV = AWS_ENDPOINT_URL=$${AWS_ENDPOINT_URL:-http://localhost:4566} \
               AWS_DEFAULT_REGION=$${AWS_DEFAULT_REGION:-us-east-1} \
               AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} \
               AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test}

test: up _check-venv  ## Roda todos os testes (sobe LocalStack se necessário)
	@$(AWS_TEST_ENV) $(PYTEST) tests/ -v --tb=short

# ── Unidade 1 — Serverless / mensageria ────────────────────────────────────────

test-u1: up _check-venv  ## U1 — todos os vídeos (fan-out + idempotência + DLQ)
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U1V7_fanout.py tests/test_U1V8_idempotencia.py tests/test_U1V9_dlq.py -v --tb=short

test-u1v7: up _check-venv  ## U1V7 — fan-out (SNS → múltiplas filas SQS)
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U1V7_fanout.py -v --tb=short

test-u1v8: up _check-venv  ## U1V8 — idempotência (escrita condicional)
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U1V8_idempotencia.py -v --tb=short

test-u1v9: up _check-venv  ## U1V9 — DLQ (ciclos de retry) — mais lentos (~2min)
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U1V9_dlq.py -v --tb=short

# ── Unidade 2 — Event Sourcing + CQRS ──────────────────────────────────────────

test-u2: up _check-venv  ## U2 — todos os vídeos (event store + replay/snapshots + CQRS)
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U2V7_event_store.py tests/test_U2V8_replay_snapshots.py tests/test_U2V9_cqrs_projecao.py -v --tb=short

test-u2v7: up _check-venv  ## U2V7 — Event Store (append-only, comandos, replay)
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U2V7_event_store.py -v --tb=short

test-u2v8: up _check-venv  ## U2V8 — Replay e Snapshots
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U2V8_replay_snapshots.py -v --tb=short

test-u2v9: up _check-venv  ## U2V9 — CQRS e Projeção (via DynamoDB Streams)
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U2V9_cqrs_projecao.py -v --tb=short

# ── Unidade 3 — Kafka + Reativa + IA ───────────────────────────────────────────

test-u3: up _check-venv  ## U3 — todos os vídeos (Kafka produtor/consumidor + IA)
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U3V7_kafka_produtor.py tests/test_U3V8_kafka_consumidor.py tests/test_U3V9_ia_classificador.py -v --tb=short

test-u3v7: up _check-venv  ## U3V7 — Produtor Kafka (publicação e particionamento por chave)
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U3V7_kafka_produtor.py -v --tb=short

test-u3v8: up _check-venv  ## U3V8 — Consumidor Kafka (commit manual, at-least-once)
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U3V8_kafka_consumidor.py -v --tb=short

test-u3v9: up _check-venv  ## U3V9 — Classificador com IA (roteamento, cache, erros)
	@$(AWS_TEST_ENV) $(PYTEST) tests/test_U3V9_ia_classificador.py -v --tb=short

# ── Deploy AWS Real ───────────────────────────────────────────────────────────

deploy-aws:  ## Deploy via SAM na AWS real (requer credenciais configuradas)
	cd infra && sam build && sam deploy --guided

# ── Limpeza ───────────────────────────────────────────────────────────────────

clean: down  ## Para o LocalStack e remove arquivos temporários
	find . -name "*.zip" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅  Ambiente limpo."

# ── Help ──────────────────────────────────────────────────────────────────────

help:  ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
