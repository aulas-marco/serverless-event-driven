# Glossário — Unidade 3

> 📌 Termos específicos de Kafka, fluxos assíncronos e processamento orientado a eventos usados ao longo da Unidade 3. Conceitos gerais de infraestrutura AWS estão no [Glossário da Unidade 1](../unidade-1/glossario.md); Event Sourcing e CQRS no [Glossário da Unidade 2](../unidade-2/glossario.md).

---

<a id="kafka"></a>
### Kafka (log persistente)

Broker de mensagens em que os eventos são gravados em um **log imutável e persistente** pelo tempo de retenção configurado. Ao contrário de filas tradicionais, consumir uma mensagem não a apaga — qualquer consumidor pode reler o log (replay) a partir do offset desejado.

---

<a id="particao"></a>
### Partição

Subdivisão de um tópico Kafka; é a **unidade de paralelismo** do sistema. Múltiplas partições permitem que vários consumidores processem em paralelo, mas a ordenação de eventos é garantida somente *dentro de uma mesma partição* — eventos de partições diferentes não têm ordem relativa garantida.

---

<a id="chave"></a>
### Chave (key)

Valor opcional associado a cada mensagem que determina para qual partição ela vai (via hash). Usar a mesma chave — por exemplo, o ID de uma conta — garante que todos os eventos daquela entidade caiam na mesma partição e, portanto, sejam processados em ordem. No código, o argumento `chave=` em `publicar(..., chave=account_id)`.

---

<a id="consumer-group"></a>
### Consumer group

Conjunto de instâncias de consumidor que cooperam para processar um tópico. O Kafka distribui as partições entre os membros do grupo de modo que **cada partição seja atribuída a exatamente uma instância** por vez. Múltiplos grupos independentes podem consumir o mesmo tópico sem interferência. No código, `criar_consumidor(group_id="...")`.

---

<a id="offset"></a>
### Offset

Número sequencial que identifica a posição de um evento no log de uma partição. O consumidor controla seu próprio offset; com `enable.auto.commit=False` o commit é feito manualmente após o processamento bem-sucedido, evitando perda de mensagens em caso de falha antes do ACK.

---

<a id="rebalanceamento"></a>
### Rebalanceamento

Redistribuição das partições entre as instâncias de um consumer group, disparada quando uma instância entra, sai ou trava. Durante o rebalanceamento, o consumo é pausado brevemente. Um `ConsumerRebalanceListener` permite commitar offsets pendentes antes que as partições sejam transferidas para outra instância.

---

<a id="semantica-de-entrega"></a>
### Semântica de entrega

Define quantas vezes um evento pode ser processado em caso de falha:

- **at-most-once** — commit antes de processar; mensagens podem ser perdidas.
- **at-least-once** — commit após processar (padrão com `enable.auto.commit=False`); pode haver reprocessamento em caso de falha, portanto o consumidor deve ser idempotente.
- **exactly-once** — requer transações Kafka e é mais custoso; raro em cenários serverless.

O padrão adotado no projeto é *at-least-once*.

---

<a id="contrapressao"></a>
### Contrapressão (backpressure)

Mecanismo pelo qual o consumidor sinaliza ao produtor o ritmo que consegue absorver, evitando acúmulo ilimitado na memória. Em Python assíncrono, `asyncio.Queue(maxsize=N)` implementa esse controle: quando a fila está cheia, o produtor aguarda antes de enfileirar novos itens.

---

<a id="asyncio"></a>
### asyncio / fluxos assíncronos

Modelo de concorrência do Python baseado em coroutines e um único loop de eventos. Permite que uma instância processe múltiplos eventos de forma intercalada sem criar threads. **Async generators** (`async def` + `yield`) produzem sequências de 0..N valores sob demanda; `asyncio.Future` representa um resultado ainda não disponível — fundamentais para pipelines reativos de eventos.

---

<a id="cache-classificacao"></a>
### Cache de classificação

Estratégia para evitar chamadas repetidas ao LLM: a classificação obtida para um texto é armazenada no DynamoDB (tabela `classificacoes`) usando como chave o hash do conteúdo, com TTL configurável. Textos idênticos retornam a classificação armazenada sem custo adicional de inferência.

---

⬅️ [Anterior: Exercícios](exercicios.md) · 📑 [Índice](index.md)
