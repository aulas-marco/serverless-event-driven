#!/usr/bin/env bash
# Remove os recursos criados pelo setup.sh.
set -euo pipefail

ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

AWS="aws --endpoint-url=${ENDPOINT} --region=${REGION}"

echo "🗑️   Removendo recursos do LocalStack ..."

$AWS sqs delete-queue --queue-url "$($AWS sqs get-queue-url --queue-name fila-estoque --query QueueUrl --output text)" 2>/dev/null || true
$AWS sqs delete-queue --queue-url "$($AWS sqs get-queue-url --queue-name fila-notificacao --query QueueUrl --output text)" 2>/dev/null || true
$AWS sqs delete-queue --queue-url "$($AWS sqs get-queue-url --queue-name fila-estoque-dlq --query QueueUrl --output text)" 2>/dev/null || true
$AWS sns delete-topic --topic-arn "$($AWS sns list-topics --query 'Topics[0].TopicArn' --output text)" 2>/dev/null || true
$AWS dynamodb delete-table --table-name mensagens-processadas 2>/dev/null || true

echo "✅  Teardown concluído."
