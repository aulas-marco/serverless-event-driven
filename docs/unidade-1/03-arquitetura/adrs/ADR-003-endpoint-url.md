# ADR-003 — Alternância LocalStack/AWS via AWS_ENDPOINT_URL

**Status:** Aceito  
**Data:** 2026-05-29  
**Autor:** Marco Mendes

## Contexto

O código dos handlers Lambda e dos testes precisa funcionar tanto no LocalStack (local) quanto na AWS Real (produção/avaliação), sem nenhuma mudança no código-fonte.

## Decisão

Usar a variável de ambiente **`AWS_ENDPOINT_URL`** como único ponto de alternância. Quando definida, `boto3` a lê automaticamente e aponta todas as chamadas para o endpoint configurado (LocalStack). Quando não definida, `boto3` usa o endpoint padrão da AWS.

```python
# Padrão adotado em TODOS os clientes boto3 deste projeto
endpoint = os.environ.get("AWS_ENDPOINT_URL")
client = boto3.client("sns", endpoint_url=endpoint)
```

Quando `endpoint` é `None`, `boto3` ignora o parâmetro — comportamento idêntico a `boto3.client("sns")`.

## Justificativa

- Zero modificação de código entre modos.
- `AWS_ENDPOINT_URL` é suportada nativamente pelo boto3 — não é uma variável inventada por este projeto.
- Padrão idêntico ao projeto `aspire-aws` (referência).
- Para o LocalStack, credenciais `test/test` são usadas quando o endpoint aponta para `localhost`.

## Modo LocalStack

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

## Modo AWS Real

```bash
unset AWS_ENDPOINT_URL
# aws configure (credenciais reais)
```

## Consequências

- `helpers.make_client()` detecta automaticamente se está em modo local pelo valor de `ENDPOINT`.
- Nenhum arquivo `.py` no `src/` menciona `localhost` ou credenciais hardcoded.
- Os testes rodam identicamente nos dois modos — exceção: testes de DLQ são mais lentos na AWS real (visibility timeout de produção é 30s; no LocalStack configuramos 10s para agilizar).
