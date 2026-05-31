# Portal da Unidade 3 — Kafka, Programação Reativa e IA aplicada a Eventos

Este portal é o guia de estudo da **Unidade 3 do curso IEC EAD — Serverless Computing e Arquiteturas Event-Driven** (PUC Minas / IEC): aqui você encontra contexto, código e trilha de aprendizagem para Kafka, fluxos assíncronos com asyncio e IA classificando eventos em tempo real, tudo implementado em Python com LocalStack e Kafka local.

---

## O que você vai aprender

- Por que o Kafka é um **log persistente e imutável** — e como isso o diferencia de uma fila comum.
- Como **partições, chaves e ordenação** determinam o paralelismo e a sequência de mensagens.
- O papel dos **grupos de consumidores** e as semânticas de entrega (at-most-once, at-least-once, exactly-once).
- Como modelar **contrapressão e fluxos assíncronos** com `asyncio` para consumir eventos sem bloquear.
- Como usar **IA para classificar eventos** de forma econômica: quando acionar o modelo e quando servir do cache.
- Como ler e relacionar o código em `src/U3_kafka/` e `src/U3_ia/` com os padrões apresentados.

---

## Como usar este portal

- **Leia na ordem** da trilha abaixo — cada página pressupõe o que veio antes.
- Cada página tem um **rodapé de trilha** com links para a anterior e a próxima, além de um atalho para este índice.
- Todo trecho de código mostrado nas páginas é fiel ao que está em `src/U3_kafka/` e `src/U3_ia/` — se quiser verificar, abra o arquivo correspondente.
- **Pré-requisito de ambiente**: o `make up` agora sobe LocalStack **e Kafka** — siga o [Setup local](../00-comece-aqui/setup-local.md) se ainda não tiver o ambiente rodando.

---

## Mapa da trilha da Unidade 3

### Fundamentos

1. [Kafka — log, partições e consumer groups](01-fundamentos/1-kafka-log-particoes.md) — log persistente, partições/chaves/ordenação, consumer groups e semânticas de entrega.
2. [Programação Reativa com asyncio](01-fundamentos/2-reativa-asyncio.md) — contrapressão e fluxos assíncronos com asyncio.
3. [IA em Eventos](01-fundamentos/3-ia-em-eventos.md) — IA classificando eventos: casos de uso e padrões econômicos.

### Demos

4. [U3V7 — Produtor Kafka](02-demos/u3v7-kafka-produtor.md) — produtor Kafka e particionamento por chave.
5. [U3V8 — Consumidor Kafka](02-demos/u3v8-kafka-consumidor.md) — consumidor, commit manual e at-least-once.
6. [U3V9 — Classificador com IA](02-demos/u3v9-classificador-ia.md) — Lambda Python classificando com IA, cache DynamoDB, roteamento SQS.

### Exercícios e Referência

7. [Exercícios](exercicios.md) — desafios práticos para fixar Kafka, reativa e IA em eventos.
8. [Glossário](glossario.md) — referência de termos e siglas de Kafka, programação reativa e IA.

---

## As três demos num relance

| Demo | Tema | Peças |
|---|---|---|
| **U3V7** | Kafka — produtor/partições | `confluent-kafka` Producer · chave→partição |
| **U3V8** | Kafka — consumidor | consumer group · commit manual · at-least-once |
| **U3V9** | IA classificando eventos | Lambda Python · Anthropic · cache DynamoDB · roteamento SQS |

---

📑 Você está no índice da Unidade 3 · [Próximo: Kafka — o log ➡️](01-fundamentos/1-kafka-log-particoes.md)

⬆️ [Portal do curso](../index.md)
