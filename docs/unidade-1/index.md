# Unidade 1 — Serverless, Eventos e Mensageria

Portal da **Unidade 1** do curso IEC EAD — Serverless e Event-Driven, em Python + LocalStack. Aqui você entende os três padrões fundamentais de mensageria event-driven e o código que os implementa.

---

## O que você vai aprender

- Os três padrões event-driven do projeto: **distribuição em leque (fan-out)**, **idempotência pelo menos uma vez** e **fila de mensagens mortas (DLQ)**.
- Relacionar o código Python em `src/` com a arquitetura AWS (Lambda, SNS, SQS, DynamoDB).
- Executar as demos localmente com LocalStack e, opcionalmente, na AWS real, sem mudar o código.
- Reconhecer as decisões de design que tornam o código testável, portável e idiomático.

---

## Como usar

- **Leia na ordem** da trilha abaixo — cada página pressupõe a anterior.
- Cada página tem um **rodapé de trilha** (anterior · índice · próximo).
- Todo trecho de código é fiel ao que está em `src/`.

---

## Trilha da Unidade 1

### Comece aqui

1. [Pré-requisitos](00-comece-aqui/pre-requisitos.md) — ferramentas necessárias e como verificar cada uma.
2. [Setup local](00-comece-aqui/setup-local.md) — ambiente virtual e subir o LocalStack.

### Fundamentos

3. [Serverless e Lambda](01-fundamentos/1-serverless-e-lambda.md) — o que é serverless e como o Lambda se encaixa.
4. [Orientado a eventos](01-fundamentos/2-orientado-a-eventos.md) — comunicação assíncrona entre serviços.
5. [Os quatro serviços](01-fundamentos/3-os-quatro-servicos.md) — Lambda, SNS, SQS e DynamoDB nas demos.
6. [Como ler o código](01-fundamentos/4-como-ler-o-codigo.md) — convenções e estrutura de `src/`.

### Demos

7. [U1V7 — Fan-out](02-demos/u1v7-fan-out.md) — uma publicação SNS se desdobra em duas filas SQS.
8. [U1V8 — Idempotência](02-demos/u1v8-idempotencia.md) — escrita condicional no DynamoDB processa exatamente uma vez.
9. [U1V9 — DLQ](02-demos/u1v9-dlq.md) — mensagem venenosa falha três vezes e vai para a fila de mensagens mortas.

### Arquitetura

10. [Arquitetura](03-arquitetura/arquitetura.md) — diagramas C4, fluxo e sequência ([diagramas completos](03-arquitetura/diagramas.md)).
11. [O padrão aws_builder.py](03-arquitetura/aws-builder.md) — como os testes encapsulam a criação de infraestrutura.
12. [Decisões (ADRs)](03-arquitetura/decisoes-adr.md) — ADR-001 a ADR-003 explicados.

### Exercícios e glossário

13. [Exercícios](exercicios.md) — desafios práticos para fixar os três padrões.
14. [Glossário](glossario.md) — siglas e termos (referência avulsa).

---

## As três demos num relance

| Demo | Padrão | Serviços |
|---|---|---|
| **U1V7** | Distribuição em leque publicar/inscrever | SNS → SQS → Lambda |
| **U1V8** | Idempotência pelo menos uma vez | SQS → Lambda → DynamoDB |
| **U1V9** | Fila de Mensagens Mortas (DLQ) | SQS + DLQ → Lambda |

---

📑 Você está no índice da Unidade 1 · [Próximo: Pré-requisitos ➡️](00-comece-aqui/pre-requisitos.md) · ⬆️ [Portal do curso](../index.md)
