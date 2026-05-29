#!/usr/bin/env bash
# Cria todos os recursos AWS (SNS, SQS, DynamoDB) no LocalStack.
# Idempotente: erros de "já existe" são ignorados.
# Este script cria a INFRAESTRUTURA; os Lambdas são deployados pelos testes via helpers.py.
set -euo pipefail

ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

AWS="aws --endpoint-url=${ENDPOINT} --region=${REGION}"

echo "🔧  Criando recursos no LocalStack (${ENDPOINT}) ..."

# ── U1V7: Fan-out ────────────────────────────────────────────────────────────

echo ""
echo "── U1V7: Fan-out ──"

TOPIC_ARN=$($AWS sns create-topic --name pedidos --query TopicArn --output text)
echo "  SNS criado: ${TOPIC_ARN}"

FILA_ESTOQUE_URL=$($AWS sqs create-queue --queue-name fila-estoque --query QueueUrl --output text)
FILA_NOTIF_URL=$($AWS sqs create-queue --queue-name fila-notificacao --query QueueUrl --output text)
echo "  SQS criadas: fila-estoque  fila-notificacao"

FILA_ESTOQUE_ARN=$($AWS sqs get-queue-attributes \
  --queue-url "$FILA_ESTOQUE_URL" --attribute-names QueueArn \
  --query Attributes.QueueArn --output text)

FILA_NOTIF_ARN=$($AWS sqs get-queue-attributes \
  --queue-url "$FILA_NOTIF_URL" --attribute-names QueueArn \
  --query Attributes.QueueArn --output text)

# Assinaturas: aqui mora o fan-out — 1 tópico → 2 filas
$AWS sns subscribe --topic-arn "$TOPIC_ARN" --protocol sqs \
  --notification-endpoint "$FILA_ESTOQUE_ARN" \
  --attributes '{"RawMessageDelivery":"true"}' > /dev/null
$AWS sns subscribe --topic-arn "$TOPIC_ARN" --protocol sqs \
  --notification-endpoint "$FILA_NOTIF_ARN" \
  --attributes '{"RawMessageDelivery":"true"}' > /dev/null
echo "  Assinaturas SNS→SQS criadas (RawMessageDelivery=true)"

# ── U1V8: Idempotência ───────────────────────────────────────────────────────

echo ""
echo "── U1V8: Idempotência ──"

$AWS dynamodb create-table \
  --table-name mensagens-processadas \
  --attribute-definitions AttributeName=messageId,AttributeType=S \
  --key-schema AttributeName=messageId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST > /dev/null 2>&1 || echo "  (tabela já existe)"

$AWS dynamodb update-time-to-live \
  --table-name mensagens-processadas \
  --time-to-live-specification "Enabled=true,AttributeName=expira_em" > /dev/null 2>&1 || true

echo "  DynamoDB: mensagens-processadas (TTL em expira_em)"

# ── U1V9: DLQ ───────────────────────────────────────────────────────────────

echo ""
echo "── U1V9: DLQ ──"

DLQ_URL=$($AWS sqs create-queue --queue-name fila-estoque-dlq --query QueueUrl --output text)
DLQ_ARN=$($AWS sqs get-queue-attributes \
  --queue-url "$DLQ_URL" --attribute-names QueueArn \
  --query Attributes.QueueArn --output text)
echo "  DLQ criada: fila-estoque-dlq"

REDRIVE="{\"deadLetterTargetArn\":\"${DLQ_ARN}\",\"maxReceiveCount\":\"3\"}"
$AWS sqs set-queue-attributes \
  --queue-url "$FILA_ESTOQUE_URL" \
  --attributes "{\"RedrivePolicy\":\"${REDRIVE}\",\"VisibilityTimeout\":\"10\"}" > /dev/null
echo "  RedrivePolicy vinculada a fila-estoque (maxReceiveCount=3, visibilityTimeout=10s)"

echo ""
echo "✅  Setup concluído."
echo ""
echo "   TOPIC_ARN=${TOPIC_ARN}"
echo "   FILA_ESTOQUE_URL=${FILA_ESTOQUE_URL}"
echo "   FILA_NOTIF_URL=${FILA_NOTIF_URL}"
echo "   DLQ_URL=${DLQ_URL}"
