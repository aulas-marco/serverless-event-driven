# Portal de Documentação — Serverless e Event-Driven

Guia de estudo do curso **IEC EAD — Serverless Computing e Arquiteturas Event-Driven** (PUC Minas / IEC).

O curso tem **três unidades**, e cada uma é **autossuficiente**: tem o seu próprio _comece aqui_, fundamentos, demos (com código fiel ao `src/`), arquitetura, exercícios e glossário. Escolha por onde começar.

---

## Unidades

### [Unidade 1 — Serverless, Eventos e Mensageria](unidade-1/index.md)
Fan-out, idempotência e DLQ com Lambda + SNS + SQS + DynamoDB. Demos U1V7, U1V8, U1V9.

### [Unidade 2 — Event Sourcing e CQRS](unidade-2/index.md)
Event store append-only, replay/snapshots e projeção via DynamoDB Streams. Demos U2V7, U2V8, U2V9.

### [Unidade 3 — Kafka, Programação Reativa e IA](unidade-3/index.md)
Kafka (produtor/consumidor), contrapressão com asyncio e classificação de eventos com IA. Demos U3V7, U3V8, U3V9.

---

## Como usar este portal

- Cada unidade tem **trilha própria**: comece-aqui → fundamentos → demos → arquitetura → exercícios → glossário.
- Todo trecho de código mostrado é **fiel ao `src/`** — abra o arquivo correspondente para conferir.
- O ambiente local usa **LocalStack**; cada unidade tem o seu _comece aqui_ com o setup específico (a Unidade 3 também sobe **Kafka**).
- As decisões de arquitetura do projeto (ADRs) estão em [Unidade 1 › Arquitetura](unidade-1/03-arquitetura/decisoes-adr.md) e são referenciadas pelas demais unidades.
