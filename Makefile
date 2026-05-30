.PHONY: up down setup test test-v7 test-v8 test-v9 test-u2 clean lint help

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

test: up _check-venv  ## Roda todos os testes (sobe LocalStack se necessário)
	@export AWS_ENDPOINT_URL=$${AWS_ENDPOINT_URL:-http://localhost:4566} && \
	 export AWS_DEFAULT_REGION=$${AWS_DEFAULT_REGION:-us-east-1} && \
	 export AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} && \
	 export AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test} && \
	 $(PYTEST) tests/ -v --tb=short

test-v7: up _check-venv  ## Roda apenas os testes do fan-out (U1V7)
	@export AWS_ENDPOINT_URL=$${AWS_ENDPOINT_URL:-http://localhost:4566} && \
	 export AWS_DEFAULT_REGION=$${AWS_DEFAULT_REGION:-us-east-1} && \
	 export AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} && \
	 export AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test} && \
	 $(PYTEST) tests/test_U1V7_fanout.py -v --tb=short

test-v8: up _check-venv  ## Roda apenas os testes de idempotência (U1V8)
	@export AWS_ENDPOINT_URL=$${AWS_ENDPOINT_URL:-http://localhost:4566} && \
	 export AWS_DEFAULT_REGION=$${AWS_DEFAULT_REGION:-us-east-1} && \
	 export AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} && \
	 export AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test} && \
	 $(PYTEST) tests/test_U1V8_idempotencia.py -v --tb=short

test-v9: up _check-venv  ## Roda apenas os testes de DLQ (U1V9) — mais lentos (~2min)
	@export AWS_ENDPOINT_URL=$${AWS_ENDPOINT_URL:-http://localhost:4566} && \
	 export AWS_DEFAULT_REGION=$${AWS_DEFAULT_REGION:-us-east-1} && \
	 export AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} && \
	 export AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test} && \
	 $(PYTEST) tests/test_U1V9_dlq.py -v --tb=short

test-u2: up _check-venv  ## Roda apenas os testes da Unidade 2 (Event Sourcing + CQRS)
	@export AWS_ENDPOINT_URL=$${AWS_ENDPOINT_URL:-http://localhost:4566} && \
	 export AWS_DEFAULT_REGION=$${AWS_DEFAULT_REGION:-us-east-1} && \
	 export AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} && \
	 export AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test} && \
	 $(PYTEST) tests/test_U2_event_store.py tests/test_U2_replay_snapshots.py tests/test_U2_cqrs_projecao.py -v --tb=short

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
