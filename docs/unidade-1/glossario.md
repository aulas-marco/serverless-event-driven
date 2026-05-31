# Glossário

> 📌 Esta é a **fonte única** de siglas do projeto. As mesmas definições estão em `tests/aws_builder.py`. Se divergirem, o código vence.

---

<a id="arn"></a>
### ARN — Amazon Resource Name

Identificador único e global de qualquer recurso AWS. Formato: `arn:aws:serviço:região:conta:recurso`

Exemplo: `arn:aws:sqs:us-east-1:000000000000:fila-estoque`

---

<a id="sns"></a>
### SNS — Simple Notification Service

Serviço de mensageria pub/sub. Produtores publicam num tópico; cada assinante recebe uma cópia.

---

<a id="sqs"></a>
### SQS — Simple Queue Service

Serviço de filas gerenciadas. Garantia de entrega: at-least-once (pelo menos uma vez). Isso significa que a mesma mensagem pode chegar mais de uma vez.

---

<a id="url"></a>
### URL — Endereço da fila SQS

No contexto SQS: endereço HTTP único da fila, usado para enviar e receber mensagens. Diferente do ARN — a URL é o ponto de acesso; o ARN é o identificador do recurso.

---

<a id="dlq"></a>
### DLQ — Dead-Letter Queue (Fila de Mensagens Mortas)

Fila SQS comum que recebe automaticamente as mensagens rejeitadas repetidamente por outra fila. Não existe um tipo especial "DLQ": o que faz uma fila ser DLQ é outra fila apontar para ela via RedrivePolicy.

---

<a id="esm"></a>
### ESM — Event Source Mapping

Vínculo que faz o SQS invocar uma Lambda automaticamente quando mensagens chegam na fila. Declarado uma vez; o SQS assume o papel de consumidor e dispara a Lambda.

---

<a id="ttl"></a>
### TTL — Time to Live

Campo de timestamp (epoch Unix) que o DynamoDB usa para apagar registros automaticamente após a data configurada. Útil para tabelas de controle que não devem crescer indefinidamente.

---

⬅️ [Anterior: Exercícios](exercicios.md) · 📑 [Índice](index.md)
