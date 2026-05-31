# Portal de Documentação — Serverless Event-Driven

Este portal é o guia de estudo do curso **IEC EAD — Serverless Computing e Arquiteturas Event-Driven** (PUC Minas / IEC): contexto, código e trilha de aprendizagem, com todo trecho de código fiel ao que está em `src/`.

---

## Unidades do curso

- **Unidade 1 — Serverless, Eventos e Mensageria** (esta trilha, abaixo): fan-out, idempotência e DLQ com Lambda + SNS + SQS + DynamoDB (demos U1V7, U1V8, U1V9).
- **Unidade 2 — [Event Sourcing e CQRS](unidade-2/index.md)**: event store append-only, replay/snapshots e projeção via DynamoDB Streams (demos U2V7, U2V8, U2V9).
- **Unidade 3 — [Kafka, Programação Reativa e IA](unidade-3/index.md)**: Kafka (produtor/consumidor), contrapressão com asyncio e classificação de eventos com IA (demos U3V7, U3V8, U3V9).

A Unidade 1 abaixo é o ponto de partida; as Unidades [2](unidade-2/index.md) e [3](unidade-3/index.md) têm suas próprias trilhas.

---

## Para quem é este portal / O que você vai aprender

- Entender os três padrões event-driven implementados no projeto: **distribuição em leque (fan-out)**, **idempotência pelo menos uma vez** e **fila de mensagens mortas (DLQ)**.
- Ler e relacionar o código Python em `src/` com a arquitetura AWS (Lambda, SNS, SQS, DynamoDB).
- Executar as demos localmente com LocalStack e, opcionalmente, na AWS real, sem nenhuma mudança de código.
- Reconhecer as decisões de design que tornam o código testável, portável e idiomático.

---

## Como usar este portal

- **Leia na ordem** da trilha abaixo — cada página pressupõe o que veio antes.
- Cada página tem um **rodapé de trilha** com links para o anterior e o próximo, além de um atalho para este índice.
- Todo trecho de código mostrado nas páginas é fiel ao que está em `src/` — se quiser verificar, abra o arquivo correspondente.
- O [Glossário](glossario.md) é uma referência avulsa; consulte quando encontrar um termo desconhecido.

---

## Mapa da trilha

### Comece aqui

1. [Pré-requisitos](00-comece-aqui/pre-requisitos.md) — ferramentas necessárias (Docker, Python, AWS CLI, SAM CLI) e como verificar cada uma.
2. [Setup local](00-comece-aqui/setup-local.md) — clonar o repositório, criar o ambiente virtual e subir o LocalStack.

### Fundamentos

3. [Serverless e Lambda](01-fundamentos/1-serverless-e-lambda.md) — o que é computação serverless e como o Lambda se encaixa nesse modelo.
4. [Orientado a eventos](01-fundamentos/2-orientado-a-eventos.md) — o modelo de comunicação assíncrona entre serviços.
5. [Os quatro serviços](01-fundamentos/3-os-quatro-servicos.md) — Lambda, SNS, SQS e DynamoDB: responsabilidade de cada um nas demos.
6. [Como ler o código](01-fundamentos/4-como-ler-o-codigo.md) — convenções do projeto, estrutura de pastas e dicas para navegar em `src/`.

### Demos

7. [U1V7 — Fan-out](02-demos/u1v7-fan-out.md) — uma publicação no SNS se desdobra em duas filas SQS independentes.
8. [U1V8 — Idempotência](02-demos/u1v8-idempotencia.md) — escrita condicional no DynamoDB garante que o mesmo pedido seja processado exatamente uma vez.
9. [U1V9 — DLQ](02-demos/u1v9-dlq.md) — mensagem venenosa falha três vezes e é roteada para a fila de mensagens mortas.

### Aprofundar

10. [Arquitetura](03-aprofundar/arquitetura.md) — diagramas C4, fluxo e sequência que descrevem o sistema como um todo.
11. [AWS Builder](03-aprofundar/aws-builder.md) — como o módulo `aws_builder.py` encapsula a criação de infraestrutura nos testes.
12. [Decisões ADR](03-aprofundar/decisoes-adr.md) — registros de decisão arquitetural (ADR-001 a ADR-003) explicados.

### Exercícios

13. [Exercícios](exercicios.md) — desafios práticos para fixar os três padrões.

### Glossário

14. [Glossário](glossario.md) — referência de siglas e termos usados no portal (consulte a qualquer momento, fora da sequência linear).

---

## As três demos num relance

| Demo | Padrão | Serviços |
|---|---|---|
| **U1V7** | Distribuição em leque publicar/inscrever | SNS → SQS → Lambda |
| **U1V8** | Idempotência pelo menos uma vez | SQS → Lambda → DynamoDB |
| **U1V9** | Fila de Mensagens Mortas (DLQ) | SQS + DLQ → Lambda |

---

📑 Você está no índice · [Próximo: Pré-requisitos ➡️](00-comece-aqui/pre-requisitos.md)
