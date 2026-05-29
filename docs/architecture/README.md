# Arquitetura — Serverless Event-Driven

Visão arquitetural das três demos em Mermaid. Estes diagramas são o "roteiro visual" do código — cada bloco corresponde a um recurso declarado em `infra/template.yaml`.

---

## Contexto (C4 Nível 1)

```mermaid
C4Context
    title Sistema de Pedidos — Escopo da Demo

    Person(aluno, "Aluno", "Executa os testes e observa o comportamento")
    System(demo, "Demo Serverless Event-Driven", "Lambda + SNS + SQS + DynamoDB")
    System_Ext(aws, "AWS / LocalStack", "Infraestrutura de computação e mensageria")

    Rel(aluno, demo, "Publica pedidos, observa logs e métricas")
    Rel(demo, aws, "Usa serviços gerenciados")
```

---

## U1V7 — Topologia Fan-out

```mermaid
flowchart LR
    subgraph Produtor
        A([Lambda A\nprodutor.py])
    end

    subgraph SNS
        T[[Tópico: pedidos]]
    end

    subgraph Fan-out["Fan-out — 1 publish → 2 entregas"]
        direction TB
        Q1([SQS: fila-estoque])
        Q2([SQS: fila-notificacao])
    end

    subgraph Consumidoras
        B([Lambda B\nestoque.py])
        C([Lambda C\nnotificacao.py])
    end

    A -- "1× publish(PedidoCriado)" --> T
    T -- "assinatura\nRawMessageDelivery=true" --> Q1
    T -- "assinatura\nRawMessageDelivery=true" --> Q2
    Q1 -- "event source mapping" --> B
    Q2 -- "event source mapping" --> C

    style Fan-out fill:#fff3cd,stroke:#ffc107
```

> **O fan-out não está no código do produtor.** Ele está nas duas assinaturas SNS→SQS configuradas no template. O produtor faz **uma** chamada `publish`; o SNS entrega **duas** cópias.

---

## U1V8 — Fluxo de Idempotência

```mermaid
sequenceDiagram
    participant SQS as SQS (fila)
    participant Lambda as Lambda\n(processa_pedido.py)
    participant DDB as DynamoDB\n(mensagens-processadas)

    Note over SQS: at-least-once: mesma mensagem pode chegar 2×

    SQS->>Lambda: Records[{body: {messageId: "P-001"}}]
    Lambda->>DDB: PutItem(messageId="P-001")\ncondition: attribute_not_exists(messageId)
    DDB-->>Lambda: SUCESSO (item criado)
    Lambda->>Lambda: processar_pedido() ← efeito colateral

    Note over SQS: reentrega da mesma mensagem

    SQS->>Lambda: Records[{body: {messageId: "P-001"}}]
    Lambda->>DDB: PutItem(messageId="P-001")\ncondition: attribute_not_exists(messageId)
    DDB-->>Lambda: ConditionalCheckFailedException
    Lambda->>Lambda: descartar silenciosamente ← sem efeito colateral
```

---

## U1V9 — Ciclo DLQ

```mermaid
stateDiagram-v2
    [*] --> FilaPrincipal: send_message(defeituoso=true)

    FilaPrincipal --> Lambda: receive (1ª vez)
    Lambda --> FilaPrincipal: RuntimeException\n→ mensagem volta\n(visibility timeout)

    FilaPrincipal --> Lambda: receive (2ª vez)
    Lambda --> FilaPrincipal: RuntimeException\n→ mensagem volta

    FilaPrincipal --> Lambda: receive (3ª vez)
    Lambda --> FilaPrincipal: RuntimeException\n→ mensagem volta

    FilaPrincipal --> DLQ: 4ª recepção\nmaxReceiveCount atingido

    DLQ --> [*]: payload retido\n(14 dias)

    note right of DLQ
        Payload preservado intacto.
        Fila principal liberada
        para mensagens saudáveis.
    end note
```

---

## Componentes e Responsabilidades

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| Lambda Produtor | `src/U1V7_fanout/produtor.py` | Publica `PedidoCriado` no SNS — 1 chamada |
| Lambda Estoque | `src/U1V7_fanout/estoque.py` | Consome `fila-estoque` via ESM |
| Lambda Notificação | `src/U1V7_fanout/notificacao.py` | Consome `fila-notificacao` via ESM |
| Lambda Processa Pedido | `src/U1V8_idempotencia/processa_pedido.py` | Processa com PutItem condicional |
| Lambda Consumidora B | `src/U1V9_dlq/consumidora_b.py` | Consome com falha proposital (DLQ demo) |
| SAM Template | `infra/template.yaml` | Declara toda a infraestrutura como código |
| Setup Script | `infra/scripts/setup.sh` | Provisiona recursos no LocalStack via CLI |
| Test Helpers | `tests/helpers.py` | `wait_until`, `deploy_lambda`, `make_client` |
