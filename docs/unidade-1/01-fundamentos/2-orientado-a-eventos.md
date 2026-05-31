# 2. Arquitetura Orientada a Eventos

## O que é arquitetura orientada a eventos

Em uma arquitetura orientada a eventos, componentes se comunicam publicando e consumindo **fatos** — coisas que aconteceram. Um fato é imutável: `PedidoCriado`, `PagamentoAprovado`, `EstoqueAtualizado`.

Os princípios fundamentais são:

1. **O produtor publica um fato** — ele registra o que aconteceu, sem saber quem vai reagir.
2. **Os consumidores reagem** — cada consumidor decide o que fazer com aquele fato.
3. **Produtor e consumidor não se conhecem** — não há chamada direta entre eles.

## Acoplado vs desacoplado

Para tornar a diferença concreta, compare os dois modelos:

**Acoplamento direto (sem eventos)**

```
Produtor
  ├── chama Fila A diretamente
  ├── chama Fila B diretamente
  └── chama Fila C diretamente
```

O produtor precisa conhecer cada consumidor. Se uma fila muda de nome ou endereço, o produtor quebra. Adicionar um quarto consumidor exige alterar o produtor.

**Desacoplamento via tópico SNS (fan-out)**

```
Produtor → publica no Tópico SNS
                ├── SNS entrega para Fila A
                ├── SNS entrega para Fila B
                └── SNS entrega para Fila C
```

O produtor conhece apenas o tópico. Os consumidores são configurados como assinantes — o produtor não sabe quantos existem nem onde estão. Adicionar um quarto consumidor não exige nenhuma mudança no produtor.

É exatamente o que este código faz:

```python
_sns.publish(TopicArn=TOPIC_ARN, Message=payload)
```

Uma única chamada. O SNS cuida do fan-out para todas as filas assinantes.

## Push vs pull — por que filas absorvem picos

O SNS opera no modelo **push**: assim que uma mensagem chega, o SNS tenta entregá-la para cada assinante imediatamente. Se um consumidor estiver lento ou indisponível, a mensagem pode ser perdida.

Uma fila SQS entre o SNS e o consumidor Lambda resolve isso com o modelo **pull**:

- A mensagem fica armazenada na fila até o consumidor estar pronto.
- Se chegarem 10 000 pedidos em 1 segundo, a fila absorve todos; as Lambdas consomem no ritmo que conseguem.
- Nenhuma mensagem é descartada por falta de capacidade momentânea.

Essa combinação SNS + SQS é o padrão *fan-out with buffering* — e é a base das três demos deste curso.

## As três garantias que as demos exploram

Este curso demonstra três propriedades que emergem desse padrão:

| Garantia | Demo |
|---|---|
| **Fan-out**: uma publicação entrega para múltiplos consumidores independentes | [U1V7 — Fan-out](../02-demos/u1v7-fan-out.md) |
| **At-least-once / idempotência**: mensagens podem ser entregues mais de uma vez; o consumidor deve ser tolerante | [U1V8 — Idempotência](../02-demos/u1v8-idempotencia.md) |
| **Dead Letter Queue (DLQ)**: mensagens que falham repetidamente são isoladas para análise, sem travar a fila principal | [U1V9 — DLQ](../02-demos/u1v9-dlq.md) |

Cada demo está no código real em `src/U1V7_fanout/`, `src/U1V8_idempotencia/` e `src/U1V9_dlq/`.

---

⬅️ [Anterior: Serverless e Lambda](1-serverless-e-lambda.md) · 📑 [Índice](../index.md) · [Próximo: Os quatro serviços](3-os-quatro-servicos.md) ➡️
