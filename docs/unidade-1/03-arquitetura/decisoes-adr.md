# Decisões de Arquitetura (ADRs)

Os três ADRs deste projeto registram as escolhas técnicas que moldaram a estrutura do código e do ambiente de testes. Cada decisão foi tomada para minimizar a carga cognitiva do aluno e maximizar o foco nos padrões serverless.

---

## ADRs

| # | Decisão | Resumo |
|---|---|---|
| [ADR-001](adrs/ADR-001-python-boto3.md) | Python + boto3 como linguagem dos handlers Lambda | Python 3.12 com boto3 foi escolhido por handlers mínimos (~5 linhas), sem etapa de build e edição inline no console AWS — reduz a carga cognitiva de tooling para audiências mistas. |
| [ADR-002](adrs/ADR-002-localstack.md) | LocalStack como ambiente de execução local | LocalStack Community via Docker Compose simula a topologia completa (SNS → SQS → Lambda) sem custo de conta AWS, usando um único ponto de alternância de endpoint. |
| [ADR-003](adrs/ADR-003-endpoint-url.md) | Alternância LocalStack/AWS via `AWS_ENDPOINT_URL` | A variável `AWS_ENDPOINT_URL` é o único ponto de chaveamento entre LocalStack e AWS real — zero modificação de código entre os dois modos. |

---

⬅️ [Anterior: aws-builder.py](aws-builder.md) · 📑 [Índice](../index.md) · [Próximo: Exercícios](../exercicios.md) ➡️
