.PHONY: up down setup test test-v7 test-v8 test-v9 clean lint help

PYTHON  := python3
PYTEST  := $(PYTHON) -m pytest
AWS     := aws --endpoint-url=$(or $(AWS_ENDPOINT_URL),http://localhost:4566) --region=$(or $(AWS_DEFAULT_REGION),us-east-1)

# ── Ambiente ──────────────────────────────────────────────────────────────────

up:  ## Sobe o LocalStack e aguarda estar pronto
	docker compose up -d
	@bash infra/scripts/wait-localstack.sh

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

install:  ## Cria o ambiente virtual e instala dependências Python
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	@echo ""
	@echo "✅  Dependências instaladas. Ative o ambiente com:"
	@echo "    source .venv/bin/activate"

# ── Testes ────────────────────────────────────────────────────────────────────

test: up  ## Roda todos os testes (sobe LocalStack se necessário)
	@export AWS_ENDPOINT_URL=$${AWS_ENDPOINT_URL:-http://localhost:4566} && \
	 export AWS_DEFAULT_REGION=$${AWS_DEFAULT_REGION:-us-east-1} && \
	 export AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} && \
	 export AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test} && \
	 $(PYTEST) tests/ -v --tb=short

test-v7: up  ## Roda apenas os testes do fan-out (U1V7)
	@export AWS_ENDPOINT_URL=$${AWS_ENDPOINT_URL:-http://localhost:4566} && \
	 export AWS_DEFAULT_REGION=$${AWS_DEFAULT_REGION:-us-east-1} && \
	 export AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} && \
	 export AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test} && \
	 $(PYTEST) tests/test_U1V7_fanout.py -v --tb=short

test-v8: up  ## Roda apenas os testes de idempotência (U1V8)
	@export AWS_ENDPOINT_URL=$${AWS_ENDPOINT_URL:-http://localhost:4566} && \
	 export AWS_DEFAULT_REGION=$${AWS_DEFAULT_REGION:-us-east-1} && \
	 export AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} && \
	 export AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test} && \
	 $(PYTEST) tests/test_U1V8_idempotencia.py -v --tb=short

test-v9: up  ## Roda apenas os testes de DLQ (U1V9) — mais lentos (~2min)
	@export AWS_ENDPOINT_URL=$${AWS_ENDPOINT_URL:-http://localhost:4566} && \
	 export AWS_DEFAULT_REGION=$${AWS_DEFAULT_REGION:-us-east-1} && \
	 export AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-test} && \
	 export AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-test} && \
	 $(PYTEST) tests/test_U1V9_dlq.py -v --tb=short

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
