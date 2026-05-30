# Portal da Unidade 2 — Event Sourcing e CQRS

Este portal é o guia de estudo da **Unidade 2 do curso IEC EAD — Serverless Computing e Arquiteturas Event-Driven** (PUC Minas / IEC): aqui você encontra contexto, código e trilha de aprendizagem para Event Sourcing e CQRS implementados em Python com LocalStack.

---

## O que você vai aprender

- Por que guardar a **história de eventos** em vez do estado atual — e que problema isso resolve.
- Como **reconstruir o estado** de um agregado por meio de replay dos eventos armazenados.
- Como usar **snapshots** para evitar replays longos sem abrir mão da auditabilidade.
- A diferença entre **comando e consulta** (CQRS) e por que separá-los simplifica a leitura e a escrita.
- Como criar uma **projeção** (`saldo_atual`) alimentada por DynamoDB Streams de forma assíncrona.
- Como ler e relacionar o código em `src/U2_event_sourcing/` com os padrões ES/CQRS.

---

## Como usar este portal

- **Leia na ordem** da trilha abaixo — cada página pressupõe o que veio antes.
- Cada página tem um **rodapé de trilha** com links para a anterior e a próxima, além de um atalho para este índice.
- Todo trecho de código mostrado nas páginas é fiel ao que está em `src/U2_event_sourcing/` — se quiser verificar, abra o arquivo correspondente.
- **Pré-requisito de ambiente**: o mesmo setup da Unidade 1 — siga o [Setup local](../00-comece-aqui/setup-local.md) se ainda não tiver o LocalStack rodando.

---

## Mapa da trilha da Unidade 2

### Fundamentos

1. [Event Sourcing](01-fundamentos/1-event-sourcing.md) — estado como sequência de eventos; tabela append-only; reconstrução por replay.
2. [CQRS e Projeções](01-fundamentos/2-cqrs-projecoes.md) — separar comando de consulta; o que é uma projeção; consistência eventual.

### Demos

3. [U2V7 — Event Store](02-demos/u2v7-event-store.md) — event store em DynamoDB com comandos depositar e sacar; estrutura do agregado.
4. [U2V8 — Replay e Snapshots](02-demos/u2v8-replay-snapshots.md) — replay completo, idempotência do replay e uso de snapshots para otimizar.
5. [U2V9 — CQRS e Projeção](02-demos/u2v9-cqrs-projecao.md) — projeção `saldo_atual` alimentada por DynamoDB Streams e comando `transferir`.

### Exercícios e Referência

6. [Exercícios](exercicios.md) — desafios práticos para fixar Event Sourcing e CQRS.
7. [Glossário](glossario.md) — referência de termos e siglas de ES/CQRS (consulte a qualquer momento).

---

## As três demos num relance

| Demo | Padrão | Peças |
|---|---|---|
| **U2V7** | Event Store append-only | DynamoDB `eventos` · agregado · comandos |
| **U2V8** | Replay e snapshots | fold · tabela `snapshots` |
| **U2V9** | CQRS / projeção | DynamoDB Streams → `saldo_atual` · `transferir` |

---

📑 Você está no índice da Unidade 2 · [Próximo: Event Sourcing ➡️](01-fundamentos/1-event-sourcing.md)

⬆️ [Portal do curso](../index.md)
