# ADR-001 — Python + boto3 como linguagem dos handlers Lambda

**Status:** Aceito  
**Data:** 2026-05-29  
**Autor:** Marco Mendes

## Contexto

O projeto cobre três demos de padrões serverless (fan-out, idempotência, DLQ) para uma audiência com background misto — não composta de desenvolvedores Java.

A alternativa natural seria Java 21 (expertise do instrutor), mas o código educacional precisa minimizar a carga cognitiva sobre tooling para maximizar o foco nos padrões arquiteturais.

## Decisão

Usar **Python 3.12** com **boto3** para todos os handlers Lambda.

## Justificativa

| Dimensão | Python 3.12 + boto3 | Java 21 + SDK v2 |
|---|---|---|
| Handler mínimo | ~5 linhas | ~30 linhas + imports |
| Build antes de deploy | Não (zip do .py) | Sim (`mvn package`) |
| Edição no console AWS | Sim (editor inline) | Não (requer JAR) |
| Cold start em demo | ~100–300ms | 1–3s (JVM) |
| boto3 no runtime | Incluso (sem deps) | Não — precisa BOM |
| Legibilidade para audiência mista | Alta | Média–Alta |

## Consequências

- Nenhum `pom.xml`, `mvn` ou JAR sombreado no projeto.
- `boto3` já vem incluso no runtime `python3.12` da Lambda — sem `requirements.txt` para demos básicas.
- Demos com dependências externas precisariam de `requirements.txt` + empacotamento via SAM.
- O padrão de endpoint override (`endpoint_url=os.environ.get("AWS_ENDPOINT_URL")`) é idêntico ao usado no projeto `aspire-aws` (ver ADR-003).
