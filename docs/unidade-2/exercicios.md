# Exercícios Práticos — Unidade 2

Experimente e observe — cada exercício propõe uma modificação pequena e cirúrgica no código para revelar o comportamento dos padrões na prática.

---

## U2V7

### Event Store: adicionar um evento, quebrar a guarda e observar o rollback

**Objetivo 1 — Novo evento de domínio**

Adicione um evento `ContaEncerrada` ao modelo e atualize o fold para reconhecê-lo.

**Passos:**

1. Em `src/U2_event_sourcing/eventos.py`, crie o dataclass `ContaEncerrada` (campos: `aggregate_id`) e adicione a entrada correspondente em `_TIPOS`.
2. Em `src/U2_event_sourcing/conta.py`, adicione o import de `ContaEncerrada` e inclua o branch no método `aplicar`:
   ```python
   elif isinstance(evento, ContaEncerrada):
       self.existe = False
   ```
3. Execute `make test` para confirmar que os testes existentes continuam passando (nenhum teste cobre o novo evento ainda — isso é intencional).
4. No REPL ou num teste rápido, grave `ContaCriada` + `DepositoRealizado(valor=100)` + `ContaEncerrada`, reconstrua com `ContaBancaria.reconstruir(eventos)` e observe `conta.existe == False` e `conta.saldo == 100`.

**Resultado esperado:** O evento é aceito sem alterar o saldo; `existe` vira `False`. O event store continua funcionando sem nenhuma mudança — novos fatos se encaixam naturalmente na sequência.

---

**Objetivo 2 — Corrupção por sobrescrita (e como a guarda previne)**

Observe o que acontece quando o `ConditionExpression` é removido do `EventStore`.

**Passos:**

1. Abra `src/U2_event_sourcing/repositorio.py` e **comente** a linha com `ConditionExpression` dentro de `_gravar_em_sequencia`:
   ```python
   # ConditionExpression="attribute_not_exists(sequencia)",
   ```
2. Execute `make test` e observe os testes de concorrência **falharem** — dois threads gravam na mesma `sequencia` sem rejeição.
3. Manualmente, chame `store.append` duas vezes para o mesmo `aggregate_id` em "paralelo" (ou simplesmente force `_gravar_em_sequencia` com a mesma sequência duas vezes): a segunda sobrescreve silenciosamente a primeira, corrompendo a sequência.
4. Restaure a linha original e confirme que `make test` volta ao verde.

**Resultado esperado:** Sem a guarda, o DynamoDB aceita a sobrescrita e o histórico é corrompido. Com ela, a segunda gravação levanta `ConditionalCheckFailedException` e o append é rejeitado atomicamente.

---

**Objetivo 3 — Saque além do saldo não grava nenhum evento**

Confirme que um comando que falha não deixa rastro no event store.

**Passos:**

1. Crie uma conta e deposite R$ 50:
   ```python
   from decimal import Decimal
   from src.U2_event_sourcing import comandos
   comandos.depositar(store, "c-teste", Decimal("50"))
   ```
2. Tente sacar R$ 200:
   ```python
   from src.U2_event_sourcing.comandos import SaldoInsuficiente
   try:
       comandos.sacar(store, "c-teste", Decimal("200"))
   except SaldoInsuficiente as e:
       print(e)
   ```
3. Consulte todos os eventos da conta:
   ```python
   store.carregar_por_agregado("c-teste")
   ```

**Resultado esperado:** A lista contém apenas `ContaCriada` e `DepositoRealizado` — nenhum `SaqueRealizado` foi gravado. O saldo reconstruído permanece R$ 50. O event store permanece íntegro.

---

## U2V8

### Replay e snapshots: baixar o limiar, forçar colisão e reconstrução do zero

**Objetivo 1 — Snapshot a cada evento**

Baixe o limiar de snapshot e compare o custo do replay com e sem ele.

**Passos:**

1. Em `src/U2_event_sourcing/snapshots.py`, localize a função `gravar_snapshot`. Por padrão ela é chamada externamente após N eventos — nos testes, ajuste a chamada para gravar um snapshot após **cada** `store.append`:
   ```python
   # Chame gravar_snapshot(ddb, store, conta_id) após cada depositar/sacar
   ```
2. Gere uma sequência longa (10+ depósitos) numa conta de teste.
3. Compare o número de itens lidos pelo DynamoDB:
   - **Sem snapshot:** `store.carregar_por_agregado` retorna todos os N eventos.
   - **Com snapshot:** `reconstruir_com_snapshot` carrega o snapshot + apenas os eventos após `ultima_sequencia`.
4. Adicione um `print(len(eventos))` antes do `ContaBancaria.reconstruir` em ambos os fluxos para observar a diferença.

**Resultado esperado:** Com snapshot a cada evento, `reconstruir_com_snapshot` sempre lê 0 eventos adicionais (snapshot cobre tudo). O saldo final é idêntico nos dois caminhos.

---

**Objetivo 2 — Colisão de sequência forçada**

Tente gravar diretamente num item já existente e observe a rejeição.

**Passos:**

1. Grave um evento normalmente para obter a sequência 1:
   ```python
   from src.U2_event_sourcing.eventos import ContaCriada, item_de_evento
   import time
   item = item_de_evento(ContaCriada(aggregate_id="c-colisao"), sequencia=1, criado_em=int(time.time()))
   tabela.put_item(Item=item)
   ```
2. Tente gravar o mesmo item (mesma `aggregate_id`, mesma `sequencia=1`) com `ConditionExpression`:
   ```python
   from botocore.exceptions import ClientError
   try:
       tabela.put_item(
           Item=item,
           ConditionExpression="attribute_not_exists(sequencia)",
       )
   except ClientError as e:
       print(e.response["Error"]["Code"])  # ConditionalCheckFailedException
   ```
3. Confirme que o item original permanece inalterado com `tabela.get_item`.

**Resultado esperado:** O DynamoDB retorna `ConditionalCheckFailedException` e o item existente não é modificado. Essa é exatamente a garantia de append-only que torna o event store seguro.

---

**Objetivo 3 — Reconstrução do zero e validação de saldo**

Confirme que replay puro e replay com snapshot chegam ao mesmo resultado.

**Passos:**

1. Crie uma conta e execute uma sequência de operações variadas:
   ```python
   comandos.depositar(store, "c-val", Decimal("200"))
   comandos.sacar(store, "c-val", Decimal("30"))
   comandos.depositar(store, "c-val", Decimal("50"))
   ```
2. Grave um snapshot após os três eventos:
   ```python
   snapshots.gravar_snapshot(ddb, store, "c-val")
   ```
3. Faça mais um depósito após o snapshot:
   ```python
   comandos.depositar(store, "c-val", Decimal("10"))
   ```
4. Compare os dois caminhos:
   ```python
   saldo_replay = ContaBancaria.reconstruir(store.carregar_por_agregado("c-val")).saldo
   saldo_snap   = snapshots.reconstruir_com_snapshot(ddb, store, "c-val")
   assert saldo_replay == saldo_snap  # ambos devem ser 230
   ```

**Resultado esperado:** Ambos os valores são `230`. O snapshot captura o estado em `ultima_sequencia=3` e aplica apenas o evento posterior, chegando ao mesmo saldo que o replay completo.

---

## U2V9

### CQRS e projeção: consistência eventual, rebuild e extensão da projeção

**Objetivo 1 — Consistência eventual na prática**

Observe a janela de tempo entre gravar um evento e o saldo aparecer na projeção.

**Passos:**

1. Consulte o saldo projetado antes de gravar qualquer evento:
   ```python
   from src.U2_event_sourcing.projecao import obter_saldo
   print(obter_saldo("c-eventual", ddb))  # 0
   ```
2. Grave um depósito via `comandos.depositar(store, "c-eventual", Decimal("100"))`.
3. Consulte `obter_saldo` **imediatamente** (antes da Lambda de projeção processar o stream).
4. Aguarde o processamento do stream (nos testes, a Lambda é invocada diretamente) e consulte novamente.

**Resultado esperado:** Na etapa 3, `obter_saldo` ainda retorna `0` — o evento foi gravado mas a projeção ainda não processou. Após o processamento, retorna `100`. Essa janela de inconsistência é inerente ao modelo CQRS com streams assíncronos.

---

**Objetivo 2 — Truncar e reconstruir a projeção**

Simule um rebuild completo da tabela de leitura a partir dos eventos.

**Passos:**

1. Após gravar alguns eventos, confirme que `obter_saldo` retorna o valor correto.
2. Apague manualmente o item da projeção:
   ```python
   tabela_saldo.delete_item(Key={"conta_id": "c-rebuild"})
   print(obter_saldo("c-rebuild", ddb))  # 0 — tabela de leitura zerada
   ```
3. Replaye todos os eventos manualmente através do `lambda_handler` simulado:
   ```python
   from src.U2_event_sourcing.projecao import lambda_handler
   eventos_raw = store.carregar_por_agregado("c-rebuild")
   # Monte os Records no formato DynamoDB Streams e chame lambda_handler
   ```
4. Consulte `obter_saldo` novamente após o replay.

**Resultado esperado:** O saldo volta ao valor correto após o reprocessamento. Isso demonstra que a projeção é sempre descartável e reconstruível — a fonte da verdade são os eventos, não a tabela de leitura.

---

**Objetivo 3 — Estender a projeção para contar transações**

Adicione um contador de transações à tabela `saldo_atual`.

**Passos:**

1. Em `src/U2_event_sourcing/projecao.py`, modifique `_aplicar` para também incrementar um campo `num_transacoes`:
   ```python
   def _aplicar(tabela, conta_id: str, delta: Decimal) -> None:
       tabela.update_item(
           Key={"conta_id": conta_id},
           UpdateExpression=(
               "SET saldo = if_not_exists(saldo, :zero) + :d, "
               "num_transacoes = if_not_exists(num_transacoes, :zero) + :um"
           ),
           ExpressionAttributeValues={
               ":d": delta,
               ":zero": Decimal("0"),
               ":um": Decimal("1"),
           },
       )
   ```
2. Execute os testes para confirmar que nenhuma asserção existente quebra.
3. Grave 3 eventos (1 `ContaCriada`, 1 `DepositoRealizado`, 1 `SaqueRealizado`) e processe o stream.
4. Consulte o item de `saldo_atual` diretamente e verifique o campo `num_transacoes`.

**Resultado esperado:** O item de `saldo_atual` contém `num_transacoes = 3`. Cada evento processado incrementa o contador, independentemente do tipo. A projeção foi estendida sem tocar no event store nem nos comandos — isolamento total entre lados de escrita e leitura.

---

⬅️ [Anterior: U2V9 — CQRS e projeção](02-demos/u2v9-cqrs-projecao.md) · 📑 [Índice](index.md) · [Próximo: Glossário](glossario.md) ➡️
