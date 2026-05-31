# Exercícios Práticos — Unidade 3

Experimente e observe — cada exercício propõe uma modificação pequena e cirúrgica no código para revelar o comportamento do Kafka e da classificação com IA na prática.

---

## U3V7

### Produtor Kafka: partições, chaves e round-robin

**Objetivo 1 — Tópico com 3 partições e redistribuição de chaves**

Observe como o número de partições altera o mapeamento das chaves ao tópico.

**Passos:**

1. Em `src/U3_kafka/produtor.py`, localize a função `criar_topico`. Crie um novo tópico (nome diferente do padrão) com `particoes=3` em vez de 6:
   ```python
   from src.U3_kafka.produtor import criar_topico
   criar_topico("pedidos-3p", particoes=3)
   ```
2. Publique 6 mensagens com chaves distintas (`"cliente-A"` até `"cliente-F"`) usando `publicar` e anote a partição devolvida em cada chamada.
3. Repita com o mesmo conjunto de chaves no tópico original de 6 partições.
4. Abra o Kafka UI (`localhost:8080`) e compare a distribuição de mensagens entre as duas configurações.

**Resultado esperado:** Chaves idênticas sempre caem na mesma partição (hash consistente), mas a partição-destino muda quando o número de partições muda. Com 3 partições, chaves que antes ficavam em partições diferentes podem acabar na mesma — a redistribuição é inevitável ao reparticionar um tópico.

---

**Objetivo 2 — Mesma chave, mesma partição, ordem garantida**

Confirme a garantia de ordenação por chave dentro de uma partição.

**Passos:**

1. Escolha uma chave fixa, por exemplo `"pedido-42"`.
2. Publique 5 eventos em sequência para esse tópico:
   ```python
   from src.U3_kafka.produtor import criar_producer, publicar
   p = criar_producer()
   for i in range(1, 6):
       part = publicar(p, "pedidos-3p", "pedido-42", {"seq": i, "status": "etapa"})
       print(f"seq={i} → partição {part}")
   ```
3. Abra o Kafka UI, selecione o tópico, filtre pela partição retornada e inspecione as mensagens.

**Resultado esperado:** Todas as 5 mensagens caem na mesma partição e aparecem no Kafka UI exatamente na ordem de publicação (`seq=1` … `seq=5`). A ordenação é garantida dentro da partição; entre partições distintas não há garantia.

---

**Objetivo 3 — Produzir sem chave e observar o round-robin**

Veja o comportamento quando nenhuma chave é fornecida.

**Passos:**

1. Publique 9 mensagens passando `chave=None`:
   ```python
   partições_usadas = []
   for i in range(9):
       part = publicar(p, "pedidos-3p", None, {"seq": i})
       partições_usadas.append(part)
   print(partições_usadas)
   ```
2. Observe a lista de partições impressa.
3. No Kafka UI, verifique a contagem de mensagens por partição.

**Resultado esperado:** As mensagens são distribuídas pelas 3 partições de forma aproximadamente uniforme (round-robin ou sticky partitioner dependendo da versão do cliente). Nenhuma garantia de ordem global existe — mensagens sem chave não têm afinidade de partição.

---

## U3V8

### Consumidor: rebalanceamento, at-least-once e consumer lag

**Objetivo 1 — Duas instâncias no mesmo `group.id` e rebalanceamento**

Observe como o Kafka divide as partições entre consumidores do mesmo grupo.

**Passos:**

1. Certifique-se de que o tópico tem ao menos 3 partições.
2. Em dois terminais separados, suba dois consumidores com o **mesmo** `group_id`:
   ```python
   # terminal 1
   from src.U3_kafka.consumidor import criar_consumidor
   c1 = criar_consumidor("grupo-demo")
   c1.subscribe(["pedidos-3p"])

   # terminal 2
   from src.U3_kafka.consumidor import criar_consumidor
   c2 = criar_consumidor("grupo-demo")
   c2.subscribe(["pedidos-3p"])
   ```
3. Faça alguns polls em cada terminal e observe as mensagens recebidas.
4. Abra o Kafka UI → **Consumer Groups** → `grupo-demo` e veja a coluna "Partições".

**Resultado esperado:** O Kafka aciona um rebalanceamento logo que a segunda instância entra. As 3 partições são divididas entre os dois consumidores (por exemplo, 2 e 1). Cada mensagem chega a apenas um consumidor do grupo — roteamento exclusivo por partição.

---

**Objetivo 2 — Exceção antes do commit força reprocessamento at-least-once**

Confirme que `processar_com_commit_manual` não commita quando o handler lança.

**Passos:**

1. Publique uma mensagem de teste no tópico.
2. Crie um handler que lança na primeira chamada mas processa normalmente na segunda (simule uma falha transitória):
   ```python
   tentativas = {"n": 0}

   def handler_falho(msg):
       tentativas["n"] += 1
       if tentativas["n"] == 1:
           raise RuntimeError("falha simulada")
       print(f"[OK] processado na tentativa {tentativas['n']}: {msg.value()}")
   ```
3. Chame `processar_com_commit_manual(consumidor, handler_falho)` duas vezes.
4. Observe o print e o offset atual no Kafka UI após cada chamada.

**Resultado esperado:** Na primeira chamada, o handler lança e o `commit` nunca é executado — o offset não avança. Na segunda chamada, o poll entrega a **mesma mensagem** de novo (at-least-once), o handler processa com sucesso e o commit acontece. O Kafka UI reflete o offset avançado somente após a segunda chamada.

---

**Objetivo 3 — Consumer lag no Kafka UI**

Observe a diferença entre o offset produzido e o offset consumido.

**Passos:**

1. Pare todos os consumidores do grupo `grupo-demo`.
2. Publique 20 mensagens com `publicar`.
3. Abra o Kafka UI → **Consumer Groups** → `grupo-demo`. Observe a coluna **Lag**.
4. Suba um consumidor e execute polling contínuo por alguns segundos; atualize a tela do Kafka UI a cada poll.

**Resultado esperado:** O lag começa em 20 (mensagens produzidas sem consumidor ativo). Conforme o consumidor processa e commita, o lag diminui partição a partição até zerar. O consumer lag é a principal métrica de saúde de um consumidor Kafka — lag crescente indica que o consumidor não acompanha o ritmo de produção.

---

## U3V9

### Classificador com IA: novas categorias, cache e fallback

**Objetivo 1 — Adicionar uma categoria ao prompt e observar o roteamento**

Estenda o classificador para reconhecer um novo tipo de e-mail.

**Passos:**

1. Em `src/U3_ia/classificador.py`, localize a string de prompt dentro de `classificar`. Adicione `"financeiro"` como terceira opção de categoria:
   ```python
   'no formato {"prioridade": "alta|baixa", "categoria": "tecnico|comercial|financeiro"}.\n\n'
   ```
2. Envie via SQS (ou chame `classificar` diretamente) um e-mail com conteúdo financeiro:
   ```python
   from src.U3_ia.classificador import classificar, usar_cliente_llm
   resultado = classificar("Preciso do boleto de renovação do contrato vencido.")
   print(resultado)
   ```
3. Verifique se `categoria` retorna `"financeiro"`.
4. No `lambda_handler`, adicione uma fila `financeiro` ao roteamento e envie uma mensagem SQS para validar o fluxo completo.

**Resultado esperado:** O LLM devolve `{"prioridade": "...", "categoria": "financeiro"}` para e-mails claramente financeiros. O `lambda_handler` roteia para a fila correta sem nenhuma alteração no event store — apenas o prompt e o roteamento foram tocados.

---

**Objetivo 2 — Mesmo e-mail duas vezes confirma cache sem chamar o LLM**

Verifique que a segunda classificação do texto idêntico resolve pelo DynamoDB.

**Passos:**

1. Crie um cliente fake que conta quantas vezes é chamado:
   ```python
   class ClienteFake:
       chamadas = 0
       def messages(self): ...  # atributo messages com método create

   # Use uma classe aninhada ou SimpleNamespace para simular a API
   from types import SimpleNamespace
   import json

   def _create(**kwargs):
       ClienteFake.chamadas += 1
       texto = SimpleNamespace(text='{"prioridade": "alta", "categoria": "tecnico"}')
       return SimpleNamespace(content=[texto])

   fake = SimpleNamespace(messages=SimpleNamespace(create=_create))
   ```
2. Injete o cliente com `usar_cliente_llm(fake)`.
3. Chame `lambda_handler` duas vezes com o **mesmo** corpo de mensagem.
4. Imprima `ClienteFake.chamadas`.

**Resultado esperado:** `ClienteFake.chamadas == 1`. A primeira chamada invoca o LLM e grava no cache DynamoDB. A segunda chamada encontra o item pelo `hash_texto` e bypassa completamente o LLM — zero chamadas adicionais, custo zero e latência mínima.

---

**Objetivo 3 — Cliente fake com JSON inválido envia para `sem-classificacao`**

Confirme o comportamento de fallback quando a resposta do LLM não é um JSON válido.

**Passos:**

1. Crie um cliente fake que devolve texto inválido:
   ```python
   from types import SimpleNamespace

   def _create_invalido(**kwargs):
       texto = SimpleNamespace(text="desculpe, não consigo classificar isso agora")
       return SimpleNamespace(content=[texto])

   fake_invalido = SimpleNamespace(messages=SimpleNamespace(create=_create_invalido))
   ```
2. Injete com `usar_cliente_llm(fake_invalido)`.
3. Certifique-se de que não há entrada no cache para o texto que vai enviar (use um texto único).
4. Chame `lambda_handler` com esse texto e verifique o log e a fila `sem-classificacao` no LocalStack.

**Resultado esperado:** O `json.loads` lança `JSONDecodeError`, o bloco `except` no `lambda_handler` é ativado, a mensagem original é enviada para a fila `sem-classificacao` e o loop continua para os próximos records. Nenhuma exceção sobe para o Lambda runtime — o fallback garante que um e-mail não classificável não interrompe o processamento dos demais.

---

⬅️ [Anterior: U3V9 — Classificador com IA](02-demos/u3v9-classificador-ia.md) · 📑 [Índice](index.md) · [Próximo: Glossário](glossario.md) ➡️
