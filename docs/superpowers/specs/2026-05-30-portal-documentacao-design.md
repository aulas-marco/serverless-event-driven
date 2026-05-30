# Portal de Documentação — Design

**Data:** 2026-05-30
**Projeto:** serverless-event-driven (curso IEC EAD — Serverless e Event-Driven, PUC Minas / IEC)
**Objetivo:** Construir um portal de documentação didático, hospedado no GitHub junto do código, que conduza o aluno do zero ao entendimento do código das três demos (U1V7, U1V8, U1V9).

---

## Decisões fundamentais (validadas com o autor)

| Decisão | Escolha | Motivo |
|---|---|---|
| **Plataforma** | Markdown puro (renderizado pelo GitHub) | Sem build novo; não adiciona toolchain ao projeto Python |
| **Profundidade** | Trilha completa | Cria a camada de fundamentos que falta hoje, antes das demos |
| **Fonte da verdade** | Alinhar ao código real | O portal deve ser espelho fiel de `src/`/`template.yaml`, não pseudocódigo |

---

## Contexto: o achado que motiva o alinhamento

Os roteiros atuais (`docs/roteiros/*.md`, não versionados) usam pseudonomes traduzidos que **não existem na AWS nem no código**. O código real e o `infra/template.yaml` usam os nomes verdadeiros:

| Conceito | Código/template real | Roteiro atual (divergente) |
|---|---|---|
| Entrega pura SNS→SQS | `RawMessageDelivery: true` | `EntregaMensagemPura: verdadeiro` |
| Escrita condicional | `ConditionExpression="attribute_not_exists(messageId)"` | `ExpressionoCondicao='atributo_nao_existe(idMensagem)'` |
| Exceção de duplicata | `ConditionalCheckFailedException` | `VerificacaoCondicionalFalhou` |
| Política de DLQ | `RedrivePolicy` / `maxReceiveCount` | `PolíticaReenvio` / `maximo_recebimentos` |
| Handler | `lambda_handler` | `gerenciador_lambda` |
| Falha proposital (U1V9) | `raise RuntimeError` | `raise ErroDeExecucao` |
| Estrutura U1V8 | helper `_reivindicar()` (claim antes do efeito) | `try/except` dentro do handler |

Detalhes ricos presentes no código real que os roteiros **não cobrem** e que o portal deve incorporar:

- A `QueuePolicy` que autoriza o SNS a entregar no SQS (pegadinha clássica de IaC).
- A condição de corrida `GetItem + PutItem` documentada em `processa_pedido.py`, resolvida pelo `PutItem` condicional atômico.
- O glossário canônico em `tests/aws_builder.py` (já inclui `ARN`, `SNS`, `SQS`, `URL`, `DLQ`, `ESM`, `TTL`).

**Regra de ouro do portal:** todo código exibido é trecho real de `src/`/`infra/template.yaml` (nomes da AWS verdadeiros; português apenas em identificadores e comentários).

---

## Arquitetura da informação

Portal 100% markdown. A navegação é feita por:

1. **Porta de entrada forte** (`docs/index.md`) — hub que apresenta a trilha e linka tudo.
2. **Rodapé de trilha** em cada página: `← anterior · 📑 índice · próximo →`.
3. **Numeração de pastas** (`00-`, `01-`...) impõe a ordem de leitura.
4. **Diagramas Mermaid** reaproveitados de `docs/architecture/README.md` dentro das aulas.

### Estrutura de arquivos

```
docs/
├── index.md                      # porta de entrada: o que é, mapa da trilha, como usar
├── 00-comece-aqui/
│   ├── pre-requisitos.md         # ferramentas, versões, conceitos mínimos
│   └── setup-local.md            # venv, make up, make test, verificar que funcionou
├── 01-fundamentos/
│   ├── 1-serverless-e-lambda.md  # Lambda, handler, cold/warm, cliente fora do handler
│   ├── 2-orientado-a-eventos.md  # produtor/consumidor, desacoplamento, push vs pull
│   ├── 3-os-quatro-servicos.md   # SNS, SQS, DynamoDB; ARN vs URL; ESM; at-least-once
│   └── 4-como-ler-o-codigo.md    # tour de src/infra/tests, endpoint_url, LocalStack↔AWS
├── 02-demos/                     # os 3 roteiros REESCRITOS, alinhados ao código real
│   ├── u1v7-fan-out.md
│   ├── u1v8-idempotencia.md
│   └── u1v9-dlq.md
├── 03-aprofundar/
│   ├── arquitetura.md            # reaproveita/linka diagramas C4 e de sequência
│   ├── aws-builder.md            # padrão construtor + glossário canônico (migra walkthrough)
│   └── decisoes-adr.md           # ponte para architecture/adrs/
├── glossario.md                  # fonte única, idêntico ao glossário de aws_builder.py
└── exercicios.md                 # desafios práticos por demo (mexer no código e observar)
```

### Tratamento dos arquivos existentes

| Arquivo atual | Destino |
|---|---|
| `docs/roteiros/*.md` (não versionado) | **Substituído** por `02-demos/*.md` (reescritos e alinhados). Pasta `roteiros/` removida. |
| `docs/architecture/README.md` + `adrs/` (versionado) | **Permanece**. `03-aprofundar/` referencia, sem duplicar conteúdo. |
| `docs/aws_builder_walkthrough.md` (não versionado) | **Migra** para `03-aprofundar/aws-builder.md`. |
| `README.md` (versionado) | Editado apenas para apontar a porta de entrada (`docs/index.md`) e corrigir os links da seção Referências. |

---

## Anatomia de cada aula de demo (`02-demos/*.md`)

Estrutura didática fixa, do conceito ao código:

1. **Objetivo de aprendizagem** + pré-requisitos (quais fundamentos ler antes).
2. **O problema** — por que o padrão existe (cenário concreto: cobrança dupla, mensagem venenosa...).
3. **A solução em um diagrama** (Mermaid reaproveitado de `architecture/`).
4. **O código real, explicado** — trechos verdadeiros de `src/`, comentados linha a linha.
5. **A infraestrutura** — trecho real de `template.yaml` (incl. `QueuePolicy`, `RedrivePolicy`).
6. **Rodar e observar** — comandos `make` + o que esperar nos logs.
7. **Pegadinhas** — ex.: race condition `GetItem+PutItem`; por que descartar duplicata em silêncio; deixar a exceção vazar para acionar a DLQ.
8. **Checklist de compreensão** (adaptado dos roteiros) + link para `exercicios.md`.

### Cobertura específica por demo

- **U1V7 (fan-out):** 1 `publish` → 2 entregas; o fan-out mora nas assinaturas, não no produtor; `RawMessageDelivery`; a `QueuePolicy` que autoriza SNS→SQS; ESM.
- **U1V8 (idempotência):** at-least-once do SQS; `PutItem` condicional atômico; race condition `GetItem+PutItem`; padrão claim-antes-do-efeito (`_reivindicar`); TTL para não crescer indefinidamente; por que a `ConditionalCheckFailedException` não pode vazar.
- **U1V9 (DLQ):** mensagem venenosa; `RedrivePolicy` + `maxReceiveCount`; deixar a exceção (`RuntimeError`) escapar do handler; ciclo de visibility timeout/retry; payload preservado na DLQ; fluxo de correção (corrigir código → reenviar da DLQ).

---

## Convenções de escrita

- **Voz orientada ao aluno:** segunda pessoa ("você vai ver..."); construir do conhecido ao novo; sempre o *porquê* antes do *como*.
- **Caixas didáticas** via blockquote do GitHub: `> 💡 Dica`, `> ⚠️ Pegadinha`, `> 📌 Conceito`.
- **Nomes reais da AWS** em todo código exibido; português só em identificadores/comentários — espelho fiel de `src/`.
- **Glossário único:** `glossario.md` reproduz o glossário de `aws_builder.py`. As páginas linkam para ele em vez de redefinir siglas localmente.
- **Links relativos** entre páginas (funcionam no render do GitHub).

---

## Fora de escopo (YAGNI)

- Gerador de site estático (MkDocs/Docusaurus), GitHub Actions, CSS ou tema.
- Qualquer alteração em `src/`, `tests/` ou `infra/template.yaml` — o portal **documenta** o código existente, não o modifica.
- Conteúdo além das três demos do escopo do curso.

A única edição fora de `docs/` é o `README.md`, e apenas para apontar a porta de entrada.

---

## Critérios de sucesso

- Um aluno que nunca viu serverless consegue, seguindo a trilha em ordem, chegar a entender o código das três demos.
- Todo trecho de código no portal bate exatamente com o que está em `src/`/`template.yaml`.
- Nenhuma sigla é usada sem estar definida no `glossario.md`.
- Cada página linka coerentemente a anterior e a próxima; a porta de entrada cobre todos os caminhos.
- `README.md` aponta para o portal sem links quebrados.
