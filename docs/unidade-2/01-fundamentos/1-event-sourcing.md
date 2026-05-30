# 1. Event Sourcing

## O problema que o CRUD esconde

Em um sistema CRUD convencional, você persiste o **estado atual**. Quando uma conta passa de R$ 1 000 para R$ 700, o banco de dados executa um `UPDATE saldo = 700`. A linha anterior desaparece.

Você sabe o saldo hoje. Você não sabe:

- Quando o dinheiro saiu.
- Se foi um saque ou uma tarifa.
- Se houve uma sequência suspeita de operações antes do saldo cair.

Em domínios onde auditoria é obrigatória — financeiro, jurídico, saúde — essa informação perdida não é um detalhe; é o coração do negócio. Reguladores não perguntam "qual é o saldo?"; eles perguntam "como você chegou nesse saldo?".

O CRUD não tem uma resposta boa para isso. Você pode adicionar tabelas de log, triggers, campos `updated_at` — mas tudo isso é remendo sobre uma estrutura que foi projetada para esquecer. Você está tentando recuperar informação que o modelo destruiu.

> ⚠️ **Ponto de Atenção**
>
> Ter uma tabela chamada `eventos` não é Event Sourcing. Só é ES quando o estado do agregado é derivado **exclusivamente** dos eventos — nunca lido de uma coluna de estado gravada diretamente. Se você persiste eventos *e* atualiza um campo `saldo` na mesma tabela, você tem um log; não tem ES.

---

## A virada: persistir fatos, não estados

Event Sourcing inverte a equação. Em vez de gravar o resultado de uma operação, você grava o **fato que aconteceu** — imutável, com carimbo de tempo, em ordem.

O estado atual passa a ser uma *consequência* desses fatos, calculada sob demanda:

```
estado = fold(eventos em ordem cronológica)
```

A analogia mais direta é o extrato bancário:

| Abordagem | Analogia |
|---|---|
| CRUD | App de banco mostrando só o saldo atual |
| Event Sourcing | Extrato completo com cada transação registrada |

O extrato é a fonte da verdade. O saldo é apenas a soma do extrato — um valor derivado que você pode recalcular a qualquer momento.

> 📌 **Conceito — [Event Sourcing](../glossario.md#event-sourcing)**
>
> Padrão em que o estado de um [agregado](../glossario.md#agregado) nunca é gravado diretamente. A fonte da verdade é a sequência imutável de eventos; o estado é sempre *derivado* fazendo o fold dessa sequência.

---

## Append-only: a garantia de imutabilidade

Para que os eventos sejam realmente a fonte da verdade, o repositório precisa ser [append-only](../glossario.md#append-only): só inserção, nunca `UPDATE` ou `DELETE`.

Neste projeto, o [Event Store](../glossario.md#event-store) é a tabela DynamoDB `eventos`, com chave composta `aggregate_id` (PK) + `sequencia` (SK). A escrita usa uma condição que rejeita qualquer tentativa de sobrescrever uma sequência já existente:

```python
ConditionExpression="attribute_not_exists(sequencia)"
```

Se a condição falhar, a operação é rejeitada — o histórico é intocável. Auditoria, então, sai de graça: você nunca precisou escrever código de auditoria separado porque os dados nunca foram alterados.

---

## Replay: reconstruindo o estado

Quando você precisa do estado atual de uma conta, não lê uma coluna `saldo`. Você busca todos os eventos daquele `aggregate_id` em ordem crescente de `sequencia` e aplica cada um. Esse processo é o [replay](../glossario.md#replay).

No projeto, a classe `ContaBancaria` (em `src/U2_event_sourcing/conta.py`) faz exatamente isso:

```python
conta = ContaBancaria.reconstruir(lista_de_eventos)
```

O método `reconstruir` percorre a lista chamando `aplicar` para cada evento. Os eventos possíveis — `ContaCriada`, `DepositoRealizado`, `SaqueRealizado` — estão definidos em `src/U2_event_sourcing/eventos.py` como dataclasses imutáveis (`frozen=True`).

> 💡 **Dica**
>
> Perceba que `ContaBancaria` não tem nenhum acesso ao banco de dados. Ela só sabe aplicar eventos. Isso não é acidente — é um invariante de design. Quem busca e persiste os eventos é o repositório; quem interpreta é o agregado. Essa separação torna o domínio testável sem infraestrutura.

---

## Snapshot: não partir do zero toda vez

O replay é correto, mas pode ficar lento. Uma conta com dez anos de histórico pode ter centenas de milhares de eventos. Percorrer todos a cada consulta não escala.

A solução é o [snapshot](../glossario.md#snapshot): uma fotografia periódica do estado gravada à parte. No replay seguinte, você carrega o snapshot mais recente e aplica apenas os eventos *posteriores* a ele.

O projeto demonstra snapshots na demo U2V8 — por ora, o importante é entender que o snapshot é uma otimização, não uma mudança no modelo. Os eventos continuam sendo a fonte da verdade; o snapshot é apenas um atalho de leitura.

---

## Os eventos são fatos de domínio, não técnicos

Um detalhe que faz diferença na prática: os eventos descrevem **o que aconteceu no negócio**, não como o sistema respondeu. Compare:

| Evento de domínio (correto) | Log técnico (não é ES) |
|---|---|
| `DepositoRealizado { valor: 300 }` | `UPDATE executado na tabela contas` |
| `SaqueRealizado { valor: 50 }` | `função handler chamada às 14:32` |
| `ContaCriada { id: "abc" }` | `item inserido no DynamoDB` |

Os eventos de domínio carregam significado para o negócio. Se você mostrar um `DepositoRealizado` para um analista financeiro, ele entende — sem precisar de contexto técnico. Essa é a linguagem que o Event Store preserva.

No projeto, os três eventos (`ContaCriada`, `DepositoRealizado`, `SaqueRealizado`) são dataclasses imutáveis em `src/U2_event_sourcing/eventos.py`. Cada um carrega apenas os campos relevantes para o domínio — sem metadados de infraestrutura misturados.

---

## Por que isso muda o jogo

Quando o estado é um fold de eventos imutáveis, você ganha propriedades que são difíceis ou impossíveis de reproduzir em CRUD:

- **Auditoria completa** — todo o histórico está no store por construção, sem código extra.
- **Depuração temporal** — você reconstrói o estado em qualquer ponto do passado limitando o replay até aquele instante.
- **Múltiplas projeções** — o mesmo stream de eventos alimenta visões diferentes do dado (tema da próxima página: CQRS).
- **Correção de bugs retroativa** — se a lógica de cálculo estava errada, você corrige o método `aplicar` e refaz o replay; o histórico permanece intacto.

Essas propriedades não são gratuitas: Event Sourcing adiciona complexidade de leitura (o replay) e exige disciplina para não contaminar o store com eventos técnicos ou para não gravar estado fora do fold. As demos da Unidade 2 mostram onde essa troca compensa e onde ela pesa.

A próxima página apresenta CQRS — o padrão que complementa o ES separando o modelo de escrita do modelo de leitura.

---

⬅️ [Anterior: Índice da Unidade 2](../index.md) · 📑 [Índice](../index.md) · [Próximo: CQRS e projeções](2-cqrs-projecoes.md) ➡️
