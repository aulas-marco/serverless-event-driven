#!/usr/bin/env bash
# Aguarda o broker Kafka responder. Polling, não sleep fixo (padrão do projeto).
set -euo pipefail

BOOTSTRAP="${KAFKA_BOOTSTRAP:-localhost:9092}"
MAX_TENTATIVAS=30
INTERVALO=2

echo "⏳  Aguardando Kafka em ${BOOTSTRAP} ..."
for i in $(seq 1 "$MAX_TENTATIVAS"); do
    if docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
        echo "✅  Kafka pronto (tentativa ${i})."
        exit 0
    fi
    echo "   tentativa ${i}/${MAX_TENTATIVAS} — aguardando ${INTERVALO}s ..."
    sleep "$INTERVALO"
done
echo "❌  Kafka não respondeu após $((MAX_TENTATIVAS * INTERVALO))s."
exit 1
