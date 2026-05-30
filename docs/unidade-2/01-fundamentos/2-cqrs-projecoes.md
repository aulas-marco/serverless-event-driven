# 2. CQRS e Projeções

## A premissa: leitura e escrita são problemas diferentes

Toda aplicação que persiste dados resolve dois problemas ao mesmo tempo — e esses dois problemas têm exigências quase opostas.

O lado da **escrita** precisa de:
- Validação de regras de negócio ("saldo suficiente?", "conta ativa?")
- Garantia de consistência — dois saques simultâneos não podem ultrapassar o saldo
- Modelo centrado no agregado, que reflete a lógica do domínio

O lado da **leitura** precisa de:
- Formato otimizado para a consulta específica — um dashboard quer `{ conta_id, saldo }`, não a lista de eventos
- Baixa latência — uma leitura não deve disparar cálculos sob demanda
- Escalabilidade independente — dashboards costumam ter muito mais leituras que escritas

Tentar satisfazer os dois lados com o mesmo modelo é o que torna sistemas difíceis de evoluir. CQRS resolve isso separando os modelos formalmente.

---

## CQRS — separar comando de consulta

> 📌 **Conceito:** [CQRS — Command Query Responsibility Segregation](../glossario.md#cqrs) é o princípio que separa o **modelo de escrita** (comandos) do **modelo de leitura** (consultas/projeções). Os dois lados evoluem de forma independente.

O fluxo de escrita funciona assim:

```
Cliente → Comando → Validação de regra de negócio → Evento gravado no Event Store
```

O fluxo de leitura funciona assim:

```
Cliente → Consulta → Leitura da Projeção (tabela otimizada)
```

Os dois caminhos nunca se cruzam em tempo de execução.

### O lado do comando

O handler de comando em `src/U2_event_sourcing/comandos.py` exemplifica bem a responsabilidade desse lado: reconstruir o estado atual, validar a regra de negócio e, se aprovado, anexar o evento ao Event Store.

```python
def sacar(store, conta_id: str, valor: Decimal) -> None:
    conta = ContaBancaria.reconstruir(store.carregar_por_agregado(conta_id))
    if valor > conta.saldo:
        raise SaldoInsuficiente(...)
    store.append(conta_id, SaqueRealizado(aggregate_id=conta_id, valor=valor))
```

Note o que **não** aparece aqui: nenhuma leitura de `saldo_atual`, nenhuma tabela de projeção. O lado de comando conhece apenas o Event Store.

### O lado da consulta

O lado de consulta lê exclusivamente da projeção — uma tabela DynamoDB `saldo_atual` mantida em formato já calculado:

```python
def obter_saldo(conta_id: str, ...) -> Decimal:
    item = tabela.get_item(Key={"conta_id": conta_id}).get("Item")
    return Decimal(str(item["saldo"])) if item else Decimal("0")
```

Sem cálculo, sem replay, sem acesso à tabela `eventos`.

> ⚠️ **Ponto de Atenção:** as responsabilidades são rígidas. O lado de **consulta** lê *da projeção*, nunca faz replay de eventos sob demanda — isso tornaria a leitura lenta e imprevisível. O lado de **comando** escreve *somente no Event Store*, nunca lê da projeção para tomar decisões — isso introduziria dependência de um estado que pode estar desatualizado.

---

## Projeções — o modelo de leitura derivado dos eventos

> 📌 **Conceito:** [Projeção](../glossario.md#projecao) é o modelo de leitura construído a partir do stream de eventos, otimizado para consultas específicas. É descartável — pode ser recriada integralmente fazendo o replay de todos os eventos.

Uma projeção não é uma cópia do Event Store. É uma visão *derivada*, reformatada para servir uma consulta específica. A mesma sequência de eventos pode alimentar projeções com formatos completamente diferentes:

| Projeção | Formato | Uso |
|---|---|---|
| `saldo_atual` | `{ conta_id, saldo }` | Dashboard, consulta de saldo |
| `extrato` | Lista de movimentações com data | Extrato do cliente |
| `contas_negativas` | Lista de contas com saldo < 0 | Alertas de risco |

### Como a projeção é mantida no projeto

No projeto, a tabela `saldo_atual` é mantida por uma Lambda acionada via **DynamoDB Streams** sobre a tabela `eventos`. Toda vez que um novo evento é gravado no Event Store, o stream dispara automaticamente a Lambda de projeção.

O handler completo está em `src/U2_event_sourcing/projecao.py`. A lógica central:

```python
def lambda_handler(event, context):
    for registro in event["Records"]:
        if registro["eventName"] != "INSERT":
            continue                    # projeção só reage a novos eventos
        tipo = novo["tipo"]["S"]
        if tipo == "DepositoRealizado":
            _aplicar(tabela, conta_id, delta)
        elif tipo == "SaqueRealizado":
            _aplicar(tabela, conta_id, -delta)
```

A função `_aplicar` usa `UpdateExpression` com `if_not_exists` para ser idempotente — se o DynamoDB Streams entregar o mesmo registro duas vezes (garantia *at-least-once*), o resultado é o mesmo. A demo U2V9 detalha esse comportamento.

---

## Consistência eventual

> 📌 **Conceito:** [Consistência eventual](../glossario.md#consistencia-eventual) significa que há um intervalo de tempo entre gravar o evento no Event Store e a projeção refletir essa mudança. Durante esse intervalo, leituras podem retornar um valor ligeiramente desatualizado — comportamento esperado, não um erro.

O fluxo assíncrono é:

```
Evento gravado na tabela `eventos`
  → DynamoDB Streams notifica a Lambda de projeção (milissegundos a segundos)
    → Lambda atualiza `saldo_atual`
      → Próxima leitura reflete o novo saldo
```

A pergunta relevante para o design do sistema é: **o negócio tolera esse atraso?**

| Caso de uso | Tolera consistência eventual? |
|---|---|
| Dashboard de saldo (exibição) | Sim — atraso de segundos é imperceptível |
| Notificação de extrato | Sim — pode ser entregue com pequeno atraso |
| Autorização financeira em tempo real | Não — precisa do estado consistente; deve usar o modelo de comando (reconstuir do Event Store) |

Quando a consistência imediata é obrigatória, o caminho correto é reconstruir o estado a partir dos eventos — é exatamente o que `ContaBancaria.reconstruir(store.carregar_por_agregado(conta_id))` faz no lado do comando.

---

## Rebuild — a projeção é descartável

Como o Event Store é a fonte da verdade, uma projeção pode ser descartada e recriada do zero a qualquer momento. O processo é direto:

1. Truncar (ou apagar) a tabela de projeção — `saldo_atual`
2. Reprocessar todos os eventos do Event Store em ordem cronológica
3. A Lambda de projeção reconstrói o estado final a partir do histórico completo

Isso tem implicações práticas importantes:

- **Migração de schema:** se a estrutura da projeção precisar mudar, basta fazer o rebuild com a nova lógica
- **Correção de bug:** se a Lambda de projeção tinha um bug que calculou valores errados, corrija o código e reconstrua
- **Nova projeção:** adicionar um novo modelo de leitura nunca exige alterar o Event Store — só criar uma nova Lambda consumidora

---

## Event Sourcing e CQRS — sinergia, não obrigatoriedade

ES e CQRS são padrões independentes. É possível usar CQRS sem Event Sourcing (separando modelos de leitura/escrita sobre um banco relacional tradicional) e é possível usar Event Sourcing sem separar explicitamente os modelos de leitura.

Mas os dois têm sinergia natural:

- O Event Store já é o stream que alimenta projeções — o DynamoDB Streams elimina qualquer infraestrutura adicional de sincronização
- A imutabilidade dos eventos torna o rebuild determinístico e confiável
- A separação de modelos deixa o replay de comando leve (só lê eventos do agregado) e a consulta leve (só lê a projeção)

No projeto, essa combinação é o que permite que `sacar` reconstrua o estado consistente via replay enquanto `obter_saldo` retorna instantaneamente da projeção — cada operação usando o caminho certo para o seu propósito.

---

⬅️ [Anterior: Event Sourcing](1-event-sourcing.md) · 📑 [Índice](../index.md) · [Próximo: Demo U2V7 — Event Store](../02-demos/u2v7-event-store.md) ➡️
