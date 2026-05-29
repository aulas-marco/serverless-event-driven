#!/usr/bin/env bash
# Aguarda o LocalStack responder no endpoint de health.
# Padrão do aspire-aws: polling em vez de sleep fixo.
set -euo pipefail

ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
MAX_TENTATIVAS=30
INTERVALO=2

echo "⏳  Aguardando LocalStack em ${ENDPOINT}/_localstack/health ..."

for i in $(seq 1 "$MAX_TENTATIVAS"); do
    if curl -sf "${ENDPOINT}/_localstack/health" > /dev/null 2>&1; then
        echo "✅  LocalStack pronto (tentativa ${i})."
        exit 0
    fi
    echo "   tentativa ${i}/${MAX_TENTATIVAS} — aguardando ${INTERVALO}s ..."
    sleep "$INTERVALO"
done

echo "❌  LocalStack não respondeu após $((MAX_TENTATIVAS * INTERVALO))s. Verifique o container."
exit 1
