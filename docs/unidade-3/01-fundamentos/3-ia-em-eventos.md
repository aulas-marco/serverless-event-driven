# 3. IA Aplicada a Eventos

## A premissa: eventos carregam sinais

Um sistema orientado a eventos não produz apenas transações — produz uma sequência densa de sinais: volume de chegada, conteúdo semântico, padrões de recorrência, desvios de comportamento. Em sistemas suficientemente ativos, esses sinais excedem a capacidade de análise humana em tempo real.

A IA não substitui a arquitetura de eventos — ela **atua sobre os eventos** para transformar sinais em decisões automatizadas:

- Um ticket de suporte chega como evento; a IA o classifica e roteia antes que qualquer humano o leia.
- Um lote de logs de erro dispara um evento; a IA identifica a causa-raiz e agrupa por padrão.
- O volume de pedidos cai 40% todo domingo; a IA ajusta a capacidade provisionada com antecedência.

O evento é sempre o ponto de entrada. O que muda é o que acontece com ele depois.

---

## Casos de uso

### Classificação e priorização

O caso mais direto: um evento chega com conteúdo textual (ticket, e-mail, formulário) e precisa ser categorizado antes de ser roteado.

O fluxo é simples:

```
Evento recebido → LLM classifica → resultado gravado → SQS roteia para fila correta
```

Na demo U3V9 (`src/U3_ia/classificador.py`), o classificador recebe e-mails, chama o Claude Haiku e retorna um JSON com `categoria`, `prioridade` e `sentimento`. O roteamento acontece em seguida, via SQS, com base nesses campos.

### Análise de logs e detecção de padrões

Logs isolados têm pouco valor; logs agrupados revelam padrões. Um consumidor Kafka pode agregar janelas de eventos de erro e enviar o resumo para um LLM que identifica causas e sugere ações — sem que uma pessoa precise varrer centenas de linhas.

### Otimização de recursos

Padrões históricos de volume (horários de pico, sazonalidade, campanhas) podem ser usados para ajuste dinâmico de capacidade — Lambda concurrency, SQS batch size, número de partições Kafka — antes que o pico chegue, não durante.

### Apoio à definição arquitetural

LLMs também são úteis fora do fluxo de produção: dado um conjunto de requisitos (volume esperado, latência, custo-alvo), o modelo pode sugerir e justificar escolhas arquiteturais — SQS vs. Kafka, DynamoDB vs. RDS, polling vs. streams.

---

## Três abordagens de classificação

Antes de escolher LLM, vale entender o espectro de opções:

| Abordagem | Como funciona | Vantagem | Limitação |
|---|---|---|---|
| **Regras** | `if "urgente" in texto:` | Execução instantânea, custo zero | Frágil — quebra com variações de linguagem |
| **ML clássico** | Modelo treinado (TF-IDF + classificador) | Alta acurácia quando bem treinado | Requer dataset rotulado e re-treino periódico |
| **LLM** | Prompt → resposta estruturada | Poder semântico imediato, zero dados de treino | Custo por chamada; latência de rede |

Na prática, sistemas robustos combinam as três camadas: regras eliminam os casos triviais, ML clássico trata o volume médio, LLM resolve os casos ambíguos ou de alto valor. A Unidade 3 foca na camada LLM — mas ela nunca deve ser a única.

---

## Padrões econômicos

> ⚠️ **Ponto de Atenção:** sem controle de custo, o uso de LLM em produção pode surpreender. Um classificador que chama um modelo grande para cada evento, sem cache, pode custar **~US$ 800/mês** com 1 milhão de eventos. Com cache de classificações e modelo pequeno, o mesmo volume cai para **~US$ 40/mês** — redução de 95%.

Quatro padrões que fazem essa diferença:

### 1. Cache de classificações

> 📌 **Conceito:** [Cache de classificação](../glossario.md#cache-classificacao) — a classificação obtida para um texto é armazenada no DynamoDB (tabela `classificacoes`) usando como chave o hash do conteúdo, com TTL configurável. Textos idênticos retornam a classificação armazenada sem nova chamada ao LLM.

Na demo U3V9, antes de chamar a API, o classificador calcula `sha256(texto)` e consulta o DynamoDB:

```python
cache = tabela.get_item(Key={"hash": hash_texto}).get("Item")
if cache:
    return cache["resultado"]
```

A segunda ocorrência de um texto idêntico — mesmo que chegue dias depois — não consome nenhum token.

### 2. Modelos pequenos primeiro

Claude Haiku custa uma fração do Claude Sonnet ou Opus. Para tarefas de classificação com output estruturado (categoria + prioridade + sentimento), o modelo menor entrega qualidade equivalente. Reserve modelos maiores para tarefas que realmente precisam de raciocínio complexo.

### 3. Heurísticas pré-LLM

Antes de enviar qualquer texto ao LLM, aplique filtros simples:

- Mensagem em branco ou com menos de 10 caracteres? Categoria `invalido`, sem chamada.
- Assunto contém `[AUTO-REPLY]`? Categoria `automatico`, sem chamada.
- Texto já classificado recentemente (cache)? Retorna direto.

Cada caso eliminado aqui é um token economizado.

### 4. Prompts com JSON estrito

Instrua o modelo a retornar exclusivamente JSON, sem explicações adicionais. O parsing de JSON é barato; a extração de campos de texto livre não é — e falha com variações de formatação.

```python
"Responda APENAS com JSON válido: {\"categoria\": ..., \"prioridade\": ..., \"sentimento\": ...}"
```

A demo U3V9 valida o retorno com `json.loads()` e trata `JSONDecodeError` como falha recuperável.

---

## Como os padrões se conectam na demo U3V9

O fluxo completo de `src/U3_ia/classificador.py`:

```
E-mail recebido
  → hash SHA-256 do conteúdo
    → consulta cache DynamoDB (tabela `classificacoes`, TTL configurável)
      → [cache hit] retorna classificação armazenada
      → [cache miss] chama Claude Haiku via SDK Python → valida JSON → grava no cache
        → roteia para fila SQS correta (urgente / normal / spam)
```

Nenhuma chamada ao LLM sem passar pelo cache. Nenhum resultado do LLM sem validação de schema. O roteamento por SQS garante que o consumidor seguinte já recebe o evento com a classificação anexada — sem precisar repetir o processo.

---

⬅️ [Anterior: Programação reativa e asyncio](2-reativa-asyncio.md) · 📑 [Índice](../index.md) · [Próximo: Demo U3V7 — Produtor Kafka](../02-demos/u3v7-kafka-produtor.md) ➡️
