# Exercícios Práticos

Experimente e observe — cada exercício propõe uma modificação pequena e cirúrgica no código para revelar o comportamento dos padrões na prática.

---

## U1V7

### Fan-out com terceira fila

**Objetivo:** Adicionar uma nova assinante ao tópico SNS sem tocar no produtor, e observar o fan-out chegar automaticamente na nova fila.

**Passos:**

1. Em `tests/aws_builder.py`, localize a classe `TopologiaFanout`.
2. Adicione a criação de uma terceira fila SQS — por exemplo, `fila-analytics`.
3. Crie uma nova assinatura do tópico SNS para essa fila (mesmo padrão das filas existentes com `RawMessageDelivery=True`).
4. No teste `test_U1V7_fanout.py`, adicione uma asserção que confirma que a mensagem chegou em `fila-analytics`.
5. Execute `make test` e observe os três `assert` passando.

**Resultado esperado:** O produtor continua fazendo **uma única** chamada `publish`; o SNS entrega **três** cópias. Nenhuma linha do `produtor.py` foi alterada.

---

## U1V8

### Idempotência na prática — deixe a duplicata escapar

**Objetivo:** Desativar a guarda do `ConditionExpression` e observar a segunda entrega sendo processada novamente.

**Passos:**

1. Abra `src/U1V8_idempotencia/processa_pedido.py`.
2. Comente o bloco que trata `ConditionalCheckFailedException` — ou remova o `ConditionExpression` do `PutItem`.
3. Execute `make test` e observe o teste de idempotência **falhar** (o efeito colateral ocorre duas vezes).
4. Restaure o bloco original e execute novamente — o teste deve passar.

**Resultado esperado:** Sem o `ConditionExpression`, o DynamoDB aceita a segunda escrita e a Lambda processa o pedido duas vezes. Com ele, a segunda entrega é descartada silenciosamente. A diferença entre os dois runs mostra exatamente o que a guarda protege.

---

## U1V9

### DLQ acelerada — uma tentativa e já era

**Objetivo:** Reduzir o `maxReceiveCount` para 1 e observar a mensagem ir direto para a DLQ após a primeira falha, depois redespachá-la manualmente.

**Passos:**

1. Em `tests/aws_builder.py`, localize `FilaComDlq` e mude `maxReceiveCount` de `3` para `1`.
2. Em `src/U1V9_dlq/consumidora_b.py`, remova (ou comente) o bloco `if pedido.get("defeituoso")` — a Lambda agora levanta exceção para qualquer mensagem.
3. Execute `make test` e observe a mensagem cair na DLQ após apenas uma tentativa.
4. Use `awslocal sqs receive-message --queue-url <url-da-dlq>` para inspecionar o payload retido.
5. Reenvie a mensagem da DLQ para a fila principal com `awslocal sqs send-message` usando o `Body` recebido.
6. Restaure `maxReceiveCount` para `3` e o bloco `if defeituoso` — confirme que o teste volta a passar.

**Resultado esperado:** Com `maxReceiveCount=1`, a primeira falha já envia para a DLQ. O payload fica retido intacto e pode ser reenviado. Observe que a fila principal fica livre para processar outras mensagens durante todo o ciclo.

---

⬅️ [Anterior: Decisões (ADRs)](03-arquitetura/decisoes-adr.md) · 📑 [Índice](index.md) · [Próximo: Glossário](glossario.md) ➡️
