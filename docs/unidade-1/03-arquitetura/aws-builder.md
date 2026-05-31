# aws_builder.py — Padrão de Infraestrutura

`tests/aws_builder.py` é uma biblioteca reutilizável que encapsula a criação de infraestrutura AWS para os testes. Não é código de produção — é uma forma didática de mostrar como construir recursos AWS sem repetição.

---

## Racional de estar em `tests/`

- **Responsabilidade:** Configuração de infraestrutura para testes, não lógica de negócio
- **Importação:** Apenas os testes (`test_U1V7_fanout.py`, `test_U1V8_idempotencia.py`, `test_U1V9_dlq.py`) importam
- **Padrão arquitetural:** Infraestrutura de teste fica em `tests/`, lado a lado com os testes que a usam

---

## Estrutura do arquivo

### Glossário de siglas (linhas 1–38)

As siglas usadas em todo o projeto — [ARN](../glossario.md#arn--amazon-resource-name), [SNS](../glossario.md#sns--simple-notification-service), [SQS](../glossario.md#sqs--simple-queue-service), [DLQ](../glossario.md#dlq--dead-letter-queue-fila-de-mensagens-mortas), [ESM](../glossario.md#esm--event-source-mapping), [TTL](../glossario.md#ttl--time-to-live) — estão definidas no [Glossário](../glossario.md), que é a fonte única de verdade. O `aws_builder.py` reproduz um resumo inline para facilitar a leitura do código; em caso de divergência, o glossário vence.

### Funções auxiliares privadas (linhas 44+)

Implementações de baixo nível que os testes não precisam chamar diretamente:

- `_obter_arn_da_fila(sqs, url)` → [ARN](../glossario.md#arn--amazon-resource-name) a partir da [URL](../glossario.md#url--endereço-da-fila-sqs)
- `_criar_tabela_deduplicacao(dynamodb)` → cria tabela com [TTL](../glossario.md#ttl--time-to-live)

Prefixo `_` indica: privadas, uso interno.

### Classes públicas (padrão Construtor)

#### `TopologiaFanout`

Encapsula a demo **U1V7 — Distribuição em leque**:

```python
topologia = TopologiaFanout(sns, sqs, lambda_client)
topologia.publicar_pedido({"id": 1, "cliente": "ACME"})
```

A classe cuida de:

- Criar o tópico [SNS](../glossario.md#sns--simple-notification-service)
- Criar as 2 filas [SQS](../glossario.md#sqs--simple-queue-service)
- Criar as 2 inscrições (SNS → SQS)
- Implantar as Lambdas consumidoras

**Responsabilidade compartilhada:**

- `aws_builder.py` configura o "teatro" (infraestrutura)
- `test_U1V7_fanout.py` encena a peça (comportamento esperado)

#### `ProcessadorDePedidos`

Encapsula a demo **U1V8 — Idempotência**:

```python
proc = ProcessadorDePedidos(sqs, dynamodb, lambda_client)
proc.processar(ordem)  # Escrita condicional garante "exatamente uma vez"
```

#### `ConsumidoraDeEstoque` + `FilaComDlq`

Encapsula a demo **U1V9 — Fila de Mensagens Mortas**:

```python
dlq_setup = FilaComDlq(sqs, lambda_client)
dlq_setup.publicar_com_falha()  # 3 tentativas → Fila de Mensagens Mortas
dlq_setup.aguardar_na_dlq()
```

---

## Padrão de uso

Nos testes:

```python
# 1. Criar a topologia
topologia = TopologiaFanout(sns_client, sqs_client, lambda_client)

# 2. Executar ação
topologia.publicar_pedido(pedido)

# 3. Verificar efeito
assert mensagem_na_fila_estoque()
assert mensagem_na_fila_notificacao()
```

Cada classe encapsula:

- **Criação de recursos** — chamadas boto3 isoladas
- **Configuração** — `RawMessageDelivery`, `RedrivePolicy`, [TTL](../glossario.md#ttl--time-to-live), etc.
- **Interface clara** — métodos com nomes de negócio, não infraestrutura

---

## Princípios aplicados

1. **NÃO Se Repita** — configuração de infraestrutura reutilizável
2. **Separação de responsabilidades** — infra em `aws_builder.py`, lógica em `test_*.py`
3. **Nomes significativos** — `TopologiaFanout` diz exatamente o que faz
4. **Uma fonte de verdade** — recurso SQS criado uma única vez, usado por todos os testes

---

## Para o instrutor

Se está reutilizando este projeto em aulas:

1. Mostre o [Glossário](../glossario.md) aos alunos — é a fonte única de siglas
2. Explique a diferença entre "configuração" (`aws_builder.py`) e "teste" (`test_*.py`)
3. Estude as classes `TopologiaFanout`, `ProcessadorDePedidos`, `FilaComDlq` como exemplos de *padrão construtor*
4. Use `tests/helpers.py` (`wait_until`, `deploy_lambda`) como padrões para testes robustos
5. O [ESM](../glossario.md#esm--event-source-mapping) (Event Source Mapping) é o mecanismo que faz o SQS invocar a Lambda automaticamente — declarado nas classes `TopologiaFanout` e `FilaComDlq`

---

⬅️ [Anterior: Arquitetura](arquitetura.md) · 📑 [Índice](../index.md) · [Próximo: Decisões (ADRs)](decisoes-adr.md) ➡️
