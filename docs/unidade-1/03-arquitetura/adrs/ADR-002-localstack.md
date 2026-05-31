# ADR-002 — LocalStack como ambiente de execução local

**Status:** Aceito  
**Data:** 2026-05-29  
**Autor:** Marco Mendes

## Contexto

Os alunos precisam executar as demos localmente sem criar recursos na AWS real. A alternativa seria usar o SAM CLI (`sam local invoke`) para executar Lambdas isoladas, mas isso não simula a topologia completa (SNS → SQS → Lambda via event source mapping).

## Decisão

Usar **LocalStack Community Edition** via Docker Compose para simular SNS, SQS, DynamoDB, Lambda e IAM localmente.

## Justificativa

- LocalStack Community suporta completamente SNS, SQS, DynamoDB e Lambda Python 3.12.
- O docker-compose com healthcheck garante que o LocalStack esteja pronto antes dos testes (polling, nunca sleep fixo — padrão do `aspire-aws`).
- Sem custo de conta AWS para executar a demo.
- Variável `AWS_ENDPOINT_URL=http://localhost:4566` é o único ponto de alternância entre LocalStack e AWS Real (ver ADR-003).

## Limitações conhecidas

| Limitação | Impacto | Mitigação |
|---|---|---|
| Lambda Java no Community | Não afeta este projeto (Python) | — |
| `sam logs` não funciona no LocalStack | Observabilidade reduzida | Usar `awslocal logs filter-log-events` |
| IAM sem validação real | Políticas aceitas sem verificação | Testar permissões no AWS Real antes de produção |
| Event source mapping tem latência maior que produção | Testes de DLQ levam ~90s | `@pytest.mark.timeout(120)` nos testes lentos |

## Consequências

- Alunos precisam ter Docker instalado.
- `make up` deve ser executado antes dos testes.
- Credenciais `test/test` são hardcoded nos clientes boto3 quando `ENDPOINT` aponta para localhost.
