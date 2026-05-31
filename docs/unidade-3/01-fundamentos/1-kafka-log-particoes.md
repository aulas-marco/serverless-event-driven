# 1. Kafka — log, partições e semânticas de entrega

## O problema que uma fila tradicional esconde

Em uma fila convencional como o SQS, a lógica é clara: você coloca uma mensagem, um consumidor a retira e ela desaparece. Isso funciona bem para tarefas pontuais — "enviar e-mail", "redimensionar imagem" — mas cria um problema silencioso quando o dado é relevante além do primeiro processamento.

Imagine que três serviços diferentes precisam reagir ao mesmo evento de "pedido confirmado". Com SQS você teria três filas separadas; o produtor precisaria conhecer cada uma delas. Se um novo serviço surgir amanhã, o código do produtor muda. E se você precisar reprocessar eventos das últimas 48 horas após corrigir um bug? Os eventos já foram apagados.

O Kafka parte de uma premissa diferente: **consumir não é apagar**.

---

## O log persistente

No Kafka, um [tópico](../glossario.md#kafka) é um log imutável e ordenado. Cada mensagem publicada é **acrescentada ao final** e permanece lá pelo tempo de retenção configurado — independentemente de quantos consumidores já a leram.

Isso muda tudo:

| Comportamento | SQS (fila) | Kafka (log) |
|---|---|---|
| Mensagem após consumida | Apagada | Permanece no log |
| Segundo consumidor | Precisa de outra fila | Lê o mesmo log |
| Replay dos últimos N dias | Impossível | Rebobina o offset |
| Quem sabe dos consumidores | O produtor (fanout manual) | O próprio consumidor |

O produtor publica uma vez. Cada consumidor mantém sua posição ([offset](../glossario.md#offset)) independentemente, e pode avançar, pausar ou recomeçar do início sem afetar os outros.

> 📌 **Conceito — [Kafka](../glossario.md#kafka)**
>
> Broker de mensagens orientado a log: eventos são escritos de forma imutável e persistente. Consumir uma mensagem não a remove — múltiplos [consumer groups](../glossario.md#consumer-group) independentes podem ler o mesmo tópico, e qualquer um pode fazer replay voltando o [offset](../glossario.md#offset) para uma posição anterior.

---

## Partições, chaves e ordenação

Um tópico único processado por uma única instância não escala. O Kafka resolve isso dividindo o tópico em [partições](../glossario.md#particao): cada partição é uma sequência independente, e diferentes instâncias podem processar partições diferentes em paralelo.

A consequência direta: **a ordenação é garantida somente dentro de uma mesma partição**. Dois eventos em partições diferentes não têm ordem relativa garantida — o Kafka não sabe qual chegou "antes" entre eles.

Para a maioria dos sistemas isso é exatamente o que se quer: pouco importa a ordem global entre "pedido da conta A" e "pedido da conta B". O que importa é que todos os eventos *da mesma conta* sejam processados em ordem.

É aí que entra a [chave](../glossario.md#chave). Quando você publica uma mensagem com chave, o Kafka aplica um hash sobre ela para decidir em qual partição a mensagem cai. **A mesma chave sempre vai para a mesma partição** — e, portanto, todos os eventos daquela entidade chegam em ordem.

No projeto, o produtor em `src/U3_kafka/produtor.py` ilustra isso:

```python
producer.produce(topico, key=chave.encode(), value=json.dumps(valor).encode(), ...)
```

Passar `account_id` como `chave` garante que todos os eventos de uma conta specific caiam na mesma partição. Sem chave, o Kafka distribui as mensagens entre partições por round-robin — paralelismo máximo, mas sem garantia de ordem por entidade.

> ⚠️ **Ponto de Atenção**
>
> O Kafka **não garante ordem global** do tópico — só por [partição](../glossario.md#particao). Se a ordem de eventos entre entidades diferentes for crítica para o seu sistema, você precisará de um mecanismo externo (timestamps de evento, sequenciadores globais). Em geral, a ordem *por entidade* é suficiente — e é o que a chave provê.

---

## Consumer groups e rebalanceamento

Múltiplas instâncias de um serviço formam um [consumer group](../glossario.md#consumer-group). O Kafka distribui as partições entre os membros do grupo com uma regra simples: **cada partição pertence a exatamente uma instância por vez**.

Se o tópico tem 4 partições e o grupo tem 2 instâncias, cada instância fica com 2 partições. Se uma terceira instância entra (escalonamento), ocorre um [rebalanceamento](../glossario.md#rebalanceamento): as partições são redistribuídas. O mesmo acontece quando uma instância cai.

Durante o rebalanceamento, o consumo é brevemente pausado. Um `ConsumerRebalanceListener` permite commitar offsets pendentes antes que as partições sejam transferidas — importante para não perder ou duplicar mensagens nessa janela.

Grupos diferentes são completamente independentes. Um grupo de "processamento de pedidos" e um de "auditoria" podem consumir o mesmo tópico sem nenhuma interferência entre si — cada um avança no próprio offset.

No projeto, o consumidor em `src/U3_kafka/consumidor.py` cria o grupo via:

```python
Consumer({"group.id": group_id, "enable.auto.commit": False, ...})
```

---

## Offset e semânticas de entrega

O [offset](../glossario.md#offset) é o número sequencial que marca onde o consumidor está no log de cada partição. Commitar o offset é o ato de dizer ao Kafka: "processei até aqui". O que acontece com mensagens ainda não commitadas quando ocorre uma falha define a [semântica de entrega](../glossario.md#semantica-de-entrega):

| Semântica | Como funciona | Risco |
|---|---|---|
| **at-most-once** | Commit *antes* de processar | Mensagem pode ser perdida se a instância cair antes de processar |
| **at-least-once** | Commit *após* processar | Mensagem pode ser reentregue se a instância cair após processar mas antes de commitar |
| **exactly-once** | Transações Kafka + produtor idempotente | Custo alto; raro em cenários serverless |

O projeto adota **at-least-once**: `enable.auto.commit=False` desliga o commit automático, e o commit é feito manualmente *após* o processamento ser concluído com sucesso:

```python
handler(msg)            # se lançar, não chega no commit
consumidor.commit(msg)  # confirma somente após sucesso
```

Se o handler lançar uma exceção, o offset não é commitado e a mensagem será reentregue no próximo poll. A consequência direta: **o consumidor precisa ser idempotente** — processar a mesma mensagem duas vezes deve produzir o mesmo resultado que processar uma vez. As demos U3V7 e U3V8 mostram esse padrão aplicado em concreto.

> 💡 **Dica**
>
> Commit automático (`enable.auto.commit=True`) parece mais simples, mas commita em intervalos de tempo — não por mensagem processada. Uma falha entre o commit automático e o fim do processamento descarta a mensagem silenciosamente. Para pipelines que não toleram perda, commit manual é o caminho correto.

---

## Conectando os conceitos

O diagrama mental que une tudo:

```
Produtor  →  Tópico (N partições)  →  Consumer Group A  →  Serviço de pedidos
                                   →  Consumer Group B  →  Serviço de auditoria
```

- **Log persistente** → múltiplos grupos, replay possível.
- **Partição + chave** → paralelismo com ordem por entidade.
- **Offset + commit manual** → at-least-once com controle explícito.

A próxima página introduz programação reativa e `asyncio` — o modelo de concorrência Python que usamos para consumir e processar eventos sem bloquear o loop.

---

⬅️ [Anterior: Índice da Unidade 3](../index.md) · 📑 [Índice](../index.md) · [Próximo: Programação reativa e asyncio](2-reativa-asyncio.md) ➡️
