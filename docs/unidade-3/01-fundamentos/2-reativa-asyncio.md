# 2. Programação Reativa com asyncio

## O problema motivador: produtor rápido, consumidor lento

Imagine um tópico Kafka recebendo mil eventos por segundo de sensores IoT. O consumidor, porém, persiste cada evento em um banco de dados e faz uma chamada HTTP de enriquecimento — e processa apenas cem por segundo. O que acontece?

Sem nenhum controle, o buffer interno cresce sem limite. Dependendo de onde o acúmulo ocorre, o resultado é um `OutOfMemoryError`, latência crescente até timeout ou, pior, perda silenciosa de eventos. O sistema não falha ruidosamente — ele se degrada até travar.

Esse desequilíbrio entre taxas de produção e consumo é o problema que a **programação reativa** foi projetada para resolver.

---

## Contrapressão: o consumidor define o ritmo

> 📌 **Conceito — [Contrapressão](../glossario.md#contrapressao)**
>
> Mecanismo pelo qual o consumidor sinaliza ao produtor o ritmo que consegue absorver, evitando acúmulo ilimitado na memória. O produtor emite sob demanda — não o máximo que consegue.

A ideia é inverter o controle: em vez do produtor empurrar (_push_) na velocidade máxima, o consumidor **puxa** (_pull_) o próximo item apenas quando estiver pronto para processá-lo. O produtor só avança quando autorizado.

Com contrapressão:

| Sem contrapressão | Com contrapressão |
|---|---|
| Produtor emite no ritmo máximo | Produtor aguarda sinal do consumidor |
| Buffer cresce sem limite | Buffer limitado por capacidade declarada |
| Sistema trava por OOM | Sistema degrada graciosamente |
| Perda silenciosa de eventos | Pressão propagada ao produtor |

---

## Em Python: do síncrono ao assíncrono

### Iteração síncrona (bloqueante)

O laço `for item in fonte:` é bloqueante: enquanto `fonte` não tiver o próximo item, a thread inteira para. Para I/O — leitura de socket, chamada HTTP, query ao banco — isso significa desperdiçar CPU esperando.

```python
for evento in consumidor_kafka:      # bloqueia até o próximo evento
    processar(evento)                 # bloqueia durante o processamento
```

Uma instância processando assim só faz uma coisa por vez.

### asyncio.Future e coroutines

`asyncio.Future` representa **um único valor ainda não disponível**. Em vez de bloquear a thread, o loop de eventos agenda outra tarefa enquanto aguarda. Uma coroutine — função declarada com `async def` — é suspensa em cada `await` e retomada quando o resultado chega.

```python
async def buscar_enriquecimento(evento):
    return await http_client.get(f"/enrich/{evento.id}")   # suspende aqui
                                                            # loop executa outra coisa
```

Isso resolve o bloqueio de I/O, mas `Future` e coroutines representam **um único resultado**. Fluxos de eventos são 0..N valores ao longo do tempo — precisamos de algo mais.

### Async generators: 0..N valores assíncronos

Um **async generator** é declarado com `async def` mais `yield` e consumido com `async for`. Ele produz múltiplos valores de forma assíncrona, um de cada vez, entregando o próximo só quando solicitado — contrapressão por construção.

```python
async def gerar_eventos(topico):
    async for mensagem in consumidor.poll():   # não bloqueia
        yield transformar(mensagem)            # entrega sob demanda

async def pipeline():
    async for evento in gerar_eventos("pedidos"):
        await persistir(evento)                # próximo yield só após este await
```

O `async for` no consumidor garante que o gerador não avança enquanto `persistir` não terminar. Nenhum buffer implícito acumula eventos não processados.

### Contrapressão concreta com asyncio.Queue

Para pipelines com produtor e consumidor em tarefas separadas, `asyncio.Queue(maxsize=N)` é o mecanismo explícito de contrapressão.

```python
fila = asyncio.Queue(maxsize=100)   # buffer limitado

async def produtor():
    async for mensagem in fonte():
        await fila.put(mensagem)    # suspende aqui quando a fila estiver cheia

async def consumidor():
    while True:
        evento = await fila.get()
        await processar(evento)     # avança na fila só quando pronto
        fila.task_done()
```

Quando a fila atinge `maxsize=100`, o `await fila.put()` suspende o produtor até que o consumidor libere espaço. A pressão se propaga: o produtor desacelera automaticamente — sem código adicional, sem polling.

> ⚠️ **Ponto de Atenção**
>
> `asyncio` é single-thread. O loop de eventos intercala coroutines, mas executa apenas uma por vez. Se qualquer passo do pipeline for **CPU-bound** — cálculo intenso, compressão, parsing pesado — ele vai bloquear o loop inteiro e eliminar o benefício da concorrência assíncrona. Para cargas CPU-bound, a alternativa é `concurrent.futures.ProcessPoolExecutor`, que distribui o trabalho entre processos reais. O critério prático: se a operação passa a maior parte do tempo esperando I/O, asyncio é o caminho; se passa processando dados, ProcessPoolExecutor.

---

## Reactive Streams e o ecossistema JVM (referência teórica)

A especificação **Reactive Streams** (Publisher / Subscriber / Subscription) formalizou os contratos de contrapressão de forma interoperável. No ecossistema JVM, o **Project Reactor** implementa essa especificação com os tipos `Flux<T>` (0..N elementos) e `Mono<T>` (0..1 elemento), usados em frameworks como Spring WebFlux.

> ⚠️ **Atenção — referência teórica apenas**
>
> Reactor, `Flux<T>` e Spring WebFlux são **ferramentas JVM**. São citados aqui porque os conceitos — Publisher, Subscriber, contrapressão via `request(n)` — transferem-se diretamente para qualquer runtime. A biblioteca Python equivalente é **RxPY** (ReactiveX para Python). No entanto, a ferramenta desta disciplina é **Python com asyncio** — async generators e `asyncio.Queue` cobrem os mesmos padrões sem dependências externas. Não use Reactor ou WebFlux como ferramentas neste projeto.

---

## Quando asyncio não é suficiente

| Cenário | Ferramenta adequada |
|---|---|
| I/O concorrente (HTTP, banco, Kafka) | `asyncio` + async generators |
| Múltiplos eventos intercalados sem threads | `asyncio` |
| Carga CPU-bound (parsing, criptografia, ML) | `concurrent.futures.ProcessPoolExecutor` |
| Mix CPU + I/O | `ProcessPoolExecutor` para CPU + `asyncio` para I/O |

---

## Esta unidade é conceitual

Esta página não tem demo de código dedicada para programação reativa — o conceito é apresentado aqui como fundamento. As demonstrações práticas da Unidade 3 abordam Kafka (demos V7 e V8) e IA aplicada a eventos (demo V9). Os padrões de contrapressão aparecem em ação nos pipelines Kafka dessas demos.

---

⬅️ [Anterior: Kafka — o log e as partições](1-kafka-log-particoes.md) · 📑 [Índice](../index.md) · [Próximo: IA aplicada a eventos](3-ia-em-eventos.md) ➡️
