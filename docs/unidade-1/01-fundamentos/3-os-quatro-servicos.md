# Os Quatro Serviços

Nas três demos deste projeto você vai encontrar sempre os mesmos quatro serviços da AWS. Esta página apresenta cada um — o que é e qual papel desempenha no código.

---

## SNS — Simple Notification Service

O [SNS](../glossario.md#sns) é um barramento pub/sub totalmente gerenciado. Você cria um **tópico** e:

- **Produtores** publicam uma mensagem no tópico (uma chamada `publish`).
- **Assinantes** recebem uma cópia independente dessa mensagem.

O produtor não precisa saber quantos ou quais assinantes existem. Nas demos, o tópico `pedidos` tem duas assinaturas [SQS](../glossario.md#sqs) — `fila-estoque` e `fila-notificacao`. Uma única publicação dispara as duas entregas: isso é o **fan-out** da U1V7.

> 📌 **Conceito — [ARN](../glossario.md#arn) vs [URL](../glossario.md#url)**
>
> Recursos [SNS](../glossario.md#sns) são identificados por um [ARN](../glossario.md#arn) (ex.: `arn:aws:sns:us-east-1:123456789012:pedidos`).
> Recursos [SQS](../glossario.md#sqs) são identificados por uma [URL](../glossario.md#url) (ex.: `https://sqs.us-east-1.amazonaws.com/123456789012/fila-estoque`).
> A distinção importa na hora de chamar as APIs: `sns.publish(TopicArn=...)` recebe um [ARN](../glossario.md#arn); `sqs.send_message(QueueUrl=...)` recebe uma [URL](../glossario.md#url).

---

## SQS — Simple Queue Service

O [SQS](../glossario.md#sqs) é um serviço de filas gerenciadas. As mensagens ficam retidas na fila até que um consumidor as leia e confirme o processamento.

Característica central: entrega **at-least-once** — a mesma mensagem pode ser entregue mais de uma vez (por exemplo, se o consumidor demorar mais do que o tempo de visibilidade). Isso significa que **o seu código precisa ser idempotente**: processar a mesma mensagem duas vezes deve produzir o mesmo efeito que processá-la uma vez.

Essa garantia é exatamente o problema resolvido na **U1V8** → veja [`../02-demos/u1v8-idempotencia.md`](../02-demos/u1v8-idempotencia.md).

Nas demos também aparece a [DLQ](../glossario.md#dlq) (Dead-Letter Queue / Fila de Mensagens Mortas): uma fila separada para onde as mensagens vão após falhar um número máximo de vezes — tema central da U1V9.

---

## Lambda

O Lambda é a plataforma de computação sem servidor da AWS. Você sobe uma função (um arquivo `.py` com um `lambda_handler`) e a AWS a executa em resposta a eventos — sem provisionar servidores.

Nas demos, cada Lambda tem um papel específico:

| Função | Arquivo | Papel |
|---|---|---|
| Lambda A (produtor) | `src/U1V7_fanout/produtor.py` | Publica evento no [SNS](../glossario.md#sns) |
| Lambda B (estoque) | `src/U1V7_fanout/estoque.py` | Consome `fila-estoque` |
| Lambda C (notificação) | `src/U1V7_fanout/notificacao.py` | Consome `fila-notificacao` |
| Processador de pedido | `src/U1V8_idempotencia/processa_pedido.py` | Escrita condicional no DynamoDB |
| Consumidora B | `src/U1V9_dlq/consumidora_b.py` | Falha proposital para demonstrar a [DLQ](../glossario.md#dlq) |

> 📌 **Conceito — [ESM](../glossario.md#esm) (Event Source Mapping)**
>
> O [ESM](../glossario.md#esm) é a configuração que conecta uma fila [SQS](../glossario.md#sqs) a uma função Lambda. Quando mensagens chegam na fila, a AWS faz a chamada para o Lambda automaticamente — sem que você precise escrever código de polling. Nas demos, os [ESMs](../glossario.md#esm) estão declarados em `infra/template.yaml`.

---

## DynamoDB

O DynamoDB é o banco de dados chave-valor totalmente gerenciado da AWS. Nas demos ele tem um papel específico: **tabela de controle de idempotência**.

Na U1V8, cada mensagem processada tem seu identificador gravado na tabela `mensagens-processadas` com uma **escrita condicional** (`attribute_not_exists`). Se a mesma mensagem chegar duas vezes:

1. Primeira entrega → item criado → efeito colateral executado.
2. Segunda entrega → condição falha (`ConditionalCheckFailedException`) → descartado silenciosamente.

A tabela também usa **[TTL](../glossario.md#ttl)** (Time to Live): cada item tem um atributo de expiração, e o DynamoDB remove os registros antigos automaticamente, evitando que a tabela cresça indefinidamente.

---

⬅️ [Anterior: Orientado a Eventos](2-orientado-a-eventos.md) · 📑 [Índice](../index.md) · [Próximo: Como Ler o Código](4-como-ler-o-codigo.md) ➡️
