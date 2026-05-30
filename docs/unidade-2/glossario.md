# Glossário — Unidade 2

> 📌 Termos específicos de Event Sourcing e CQRS usados ao longo da Unidade 2. Os conceitos gerais de infraestrutura AWS estão no [Glossário da Unidade 1](../glossario.md).

---

<a id="event-sourcing"></a>
### Event Sourcing (ES)

Padrão em que o estado de um agregado **nunca é gravado diretamente**; em vez disso, persiste-se a sequência imutável de fatos que o modificaram. O estado atual é sempre *derivado* aplicando esses eventos em ordem. Em `conta_bancaria/domain.py`, o método `apply` traduz cada evento no delta de saldo correspondente.

---

<a id="event-store"></a>
### Event Store

O repositório append-only onde os eventos vivem. Neste projeto, é a tabela DynamoDB `eventos`, com chave composta `aggregate_id` (PK) + `sequencia` (SK). Nunca há UPDATE nem DELETE; cada nova operação acrescenta uma linha.

---

<a id="append-only"></a>
### Append-only

Restrição que garante que o histórico seja imutável: novos eventos só são inseridos, jamais sobrescritos. A `ConditionExpression="attribute_not_exists(sequencia)"` em `event_store.py` faz o DynamoDB rejeitar qualquer tentativa de reescrever uma sequência já existente.

---

<a id="agregado"></a>
### Agregado

Unidade de consistência do domínio — aqui, a classe `ContaBancaria`. Seu estado (`saldo`, `ativa`) não é lido do banco diretamente; é reconstruído fazendo o *fold* dos eventos recuperados do Event Store.

---

<a id="replay"></a>
### Replay (reconstrução)

Processo de recalcular o estado atual percorrendo todos os eventos de um agregado em ordem crescente de sequência e aplicando cada um. É o inverso de gravar: em vez de ler uma linha de estado, você "reexecuta a história". Pode partir de um snapshot para reduzir o número de eventos a processar.

---

<a id="snapshot"></a>
### Snapshot

Fotografia periódica do estado de um agregado, salva na tabela `snapshots`. Permite que o replay comece a partir de um ponto recente em vez de processar o histórico completo — essencial quando uma conta acumula milhares de transações.

---

<a id="cqrs"></a>
### CQRS — Command Query Responsibility Segregation

Princípio que separa o **modelo de escrita** (comandos que geram eventos) do **modelo de leitura** (consultas sobre projeções). Os dois lados evoluem de forma independente: a escrita garante consistência; a leitura é otimizada para velocidade e formato de consulta.

---

<a id="projecao"></a>
### Projeção

Modelo de leitura construído a partir do stream de eventos. Aqui, a tabela `saldo_atual` é mantida por uma Lambda acionada via DynamoDB Streams: a cada evento gravado na tabela `eventos`, a Lambda atualiza o saldo projetado. A projeção é descartável — pode ser recriada integralmente fazendo o replay de todos os eventos.

---

<a id="consistencia-eventual"></a>
### Consistência eventual

Característica inerente ao modelo assíncrono: há um intervalo de tempo entre o momento em que um evento é gravado no Event Store e o momento em que a projeção reflete essa mudança. Durante esse intervalo, leituras de `saldo_atual` podem retornar um valor ligeiramente desatualizado — comportamento esperado e documentado, não um erro.

---

⬅️ [Anterior: Exercícios](exercicios.md) · 📑 [Índice](index.md)
