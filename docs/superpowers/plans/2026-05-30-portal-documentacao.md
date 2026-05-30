# Portal de Documentação Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um portal de documentação em markdown puro, dentro de `docs/`, que conduza o aluno do zero ao entendimento do código das três demos (U1V7, U1V8, U1V9), com todo código exibido fiel ao real.

**Architecture:** Árvore de `.md` renderizada pelo GitHub. Navegação por uma porta de entrada (`docs/index.md`), rodapé de trilha em cada página e numeração de pastas. Diagramas Mermaid reaproveitados de `docs/architecture/`. Glossário único em `docs/glossario.md` copiado de `tests/aws_builder.py`.

**Tech Stack:** Markdown (GitHub Flavored), Mermaid (já renderizado pelo GitHub), Python 3 só para o script de verificação de links. Nenhum gerador de site.

---

## Regras transversais (valem para todas as tasks)

1. **Fidelidade de código (regra de ouro):** todo bloco de código que representa o projeto é **copiado verbatim** do arquivo real (`src/`, `infra/template.yaml`, `tests/`). Nunca redigitar de memória. Use `sed -n 'A,Bp' arquivo` para extrair e cole exatamente.
2. **Voz didática:** segunda pessoa ("você vai ver..."), do conhecido ao novo, *porquê* antes do *como*.
3. **Caixas didáticas** via blockquote: `> 💡 **Dica**`, `> ⚠️ **Pegadinha**`, `> 📌 **Conceito**`.
4. **Siglas** nunca redefinidas localmente — sempre linkam para `../glossario.md` (ajuste o `../` conforme a profundidade da pasta).
5. **Rodapé de trilha** ao fim de cada página (formato fixo abaixo).
6. **Commits frequentes** — um commit por task. Mensagens em português. Sufixo de co-autoria conforme padrão do repositório.

### Verificação de links (comando reutilizável `VERIFICA_LINKS`)

Roda da raiz do repo. Falha (exit 1) se algum link relativo apontar para arquivo inexistente:

```bash
python3 - <<'PY'
import re, os, glob, sys
ruins = []
for md in glob.glob('docs/**/*.md', recursive=True):
    base = os.path.dirname(md)
    texto = open(md, encoding='utf-8').read()
    for m in re.finditer(r'(?<!!)\[[^\]]*\]\(([^)]+)\)', texto):
        link = m.group(1).split('#')[0].strip()
        if not link or link.startswith(('http://', 'https://', 'mailto:')):
            continue
        alvo = os.path.normpath(os.path.join(base, link))
        if not os.path.exists(alvo):
            ruins.append((md, link))
for md, link in ruins:
    print(f'LINK QUEBRADO: {md} -> {link}')
print('OK: nenhum link quebrado' if not ruins else f'{len(ruins)} link(s) quebrado(s)')
sys.exit(1 if ruins else 0)
PY
```

### Rodapé de trilha (template)

Cada página termina com (ajustando alvos e `../`):

```markdown
---

⬅️ Anterior: Título · 📑 Índice · Próximo: Título ➡️
```

Página inicial não tem "Anterior"; última da trilha não tem "Próximo".

---

## Ordem da trilha (canônica)

Esta é a sequência de navegação que os rodapés e o índice devem refletir:

1. `index.md`
2. `00-comece-aqui/pre-requisitos.md`
3. `00-comece-aqui/setup-local.md`
4. `01-fundamentos/1-serverless-e-lambda.md`
5. `01-fundamentos/2-orientado-a-eventos.md`
6. `01-fundamentos/3-os-quatro-servicos.md`
7. `01-fundamentos/4-como-ler-o-codigo.md`
8. `02-demos/u1v7-fan-out.md`
9. `02-demos/u1v8-idempotencia.md`
10. `02-demos/u1v9-dlq.md`
11. `03-aprofundar/arquitetura.md`
12. `03-aprofundar/aws-builder.md`
13. `03-aprofundar/decisoes-adr.md`
14. `exercicios.md`
15. `glossario.md` (referência, fora da sequência linear — linkada de todos)

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `docs/glossario.md` | Fonte única de siglas (cópia do bloco de `tests/aws_builder.py`) |
| `docs/index.md` | Porta de entrada: o que é, mapa da trilha, como usar |
| `docs/00-comece-aqui/pre-requisitos.md` | Ferramentas, versões, conceitos mínimos |
| `docs/00-comece-aqui/setup-local.md` | venv, `make up`, `make test`, verificar sucesso |
| `docs/01-fundamentos/1-serverless-e-lambda.md` | Lambda, handler, cold/warm, cliente fora do handler |
| `docs/01-fundamentos/2-orientado-a-eventos.md` | Produtor/consumidor, desacoplamento, push vs pull |
| `docs/01-fundamentos/3-os-quatro-servicos.md` | SNS, SQS, DynamoDB; ARN vs URL; ESM; at-least-once |
| `docs/01-fundamentos/4-como-ler-o-codigo.md` | Tour de `src/`/`infra/`/`tests/`; `endpoint_url`; LocalStack↔AWS |
| `docs/02-demos/u1v7-fan-out.md` | Aula da demo fan-out |
| `docs/02-demos/u1v8-idempotencia.md` | Aula da demo idempotência |
| `docs/02-demos/u1v9-dlq.md` | Aula da demo DLQ |
| `docs/03-aprofundar/arquitetura.md` | Diagramas C4/sequência; ponte para `architecture/` |
| `docs/03-aprofundar/aws-builder.md` | Padrão construtor (migra `aws_builder_walkthrough.md`) |
| `docs/03-aprofundar/decisoes-adr.md` | Ponte para `architecture/adrs/` |
| `docs/exercicios.md` | Desafios práticos por demo |
| `README.md` (modificar) | Apontar para `docs/index.md`; corrigir seção Referências |
| `docs/roteiros/` (remover) | Substituída por `02-demos/` |
| `docs/aws_builder_walkthrough.md` (remover) | Migrada para `03-aprofundar/aws-builder.md` |

---

### Task 1: Estrutura de pastas + glossário (fonte única)

**Files:**
- Create: `docs/00-comece-aqui/`, `docs/01-fundamentos/`, `docs/02-demos/`, `docs/03-aprofundar/` (pastas)
- Create: `docs/glossario.md`

- [ ] **Step 1: Criar as pastas**

```bash
cd /Users/marco.mendes/code/serverless-event-driven
mkdir -p docs/00-comece-aqui docs/01-fundamentos docs/02-demos docs/03-aprofundar
```

- [ ] **Step 2: Extrair o glossário canônico do código**

Run: `sed -n '/Glossário de siglas/,/^"""/p' tests/aws_builder.py`
Expected: imprime o bloco com ARN, SNS, SQS, URL, DLQ, ESM, TTL.

- [ ] **Step 3: Escrever `docs/glossario.md`**

Cabeçalho didático + as 7 siglas **exatamente** com as definições de `aws_builder.py` (copiar verbatim o conteúdo textual de cada sigla; converter o layout de docstring para markdown — cada sigla como subtítulo `### ARN — Amazon Resource Name` seguido da definição). Acrescentar nota no topo:

```markdown
# Glossário

> 📌 Esta é a **fonte única** de siglas do projeto. As mesmas definições estão em `tests/aws_builder.py`. Se divergirem, o código vence.
```

Ordem: ARN, SNS, SQS, URL, DLQ, ESM, TTL. Não inventar siglas novas.

- [ ] **Step 4: Verificar fidelidade do glossário**

Run: `grep -c "RedrivePolicy" docs/glossario.md` (a definição de DLQ menciona RedrivePolicy)
Expected: `1` ou mais.

- [ ] **Step 5: Commit**

```bash
git add docs/glossario.md
git commit -m "docs(portal): glossário único de siglas (fonte: aws_builder.py)"
```

---

### Task 2: Porta de entrada (`docs/index.md`)

**Files:**
- Create: `docs/index.md`

- [ ] **Step 1: Escrever `docs/index.md`**

Seções obrigatórias:
1. **Título + uma frase** do que é o portal (curso IEC EAD — Serverless e Event-Driven).
2. **Para quem é / o que você vai aprender** — bullets dos resultados de aprendizagem (entender os 3 padrões e o código que os implementa).
3. **Como usar este portal** — ler na ordem; cada página tem rodapé de trilha; código mostrado é fiel ao `src/`.
4. **Mapa da trilha** — lista numerada com link para cada página, na ordem canônica (seção "Ordem da trilha"), agrupada por etapa (Comece aqui / Fundamentos / Demos / Aprofundar / Exercícios / Glossário). Cada item com uma linha do que cobre.
5. **As três demos num relance** — a tabela do README atual (U1V7/U1V8/U1V9 × padrão × serviços).
6. Rodapé: apenas `📑 índice` (é a própria home) e `Próximo: Pré-requisitos ➡️`.

> Reaproveite a tabela das três demos que já existe em `README.md` (linhas da seção "As três demonstrações").

- [ ] **Step 2: Verificar links**

Run: `VERIFICA_LINKS` (comando reutilizável acima)
Expected: `OK: nenhum link quebrado`
Nota: links para páginas ainda não criadas vão falhar agora — é esperado até a Task 9. Nesta task, confira manualmente que os caminhos digitados batem com a "Ordem da trilha". A verificação dura só passa na Task 10.

- [ ] **Step 3: Commit**

```bash
git add docs/index.md
git commit -m "docs(portal): porta de entrada com mapa da trilha"
```

---

### Task 3: Comece aqui (pré-requisitos + setup)

**Files:**
- Create: `docs/00-comece-aqui/pre-requisitos.md`
- Create: `docs/00-comece-aqui/setup-local.md`

- [ ] **Step 1: Extrair a tabela de pré-requisitos e o quick start reais**

Run: `sed -n '/## Pré-requisitos/,/## Modo AWS Real/p' README.md`
Expected: imprime a tabela de ferramentas e o bloco Quick Start.

- [ ] **Step 2: Escrever `pre-requisitos.md`**

- Tabela de ferramentas (Docker, Python, make, AWS CLI v2, SAM) **copiada** do README, com a coluna "Para quê".
- Nota sobre `make` no Mac (Xcode CLI Tools) — copiar do README.
- **Conceitos mínimos**: bullets curtos do que ajuda saber antes (linha de comando, Python básico, JSON). Tom acolhedor: "não precisa ser especialista em AWS — a trilha constrói isso".
- Rodapé de trilha: Anterior = `../index.md`; Próximo = `setup-local.md`.

- [ ] **Step 3: Escrever `setup-local.md`**

Passo a passo, cada um com o comando real e **o que esperar**:
1. Clonar + `cd`.
2. `make install` (cria `.venv` com Python 3.13/3.x e instala deps) — mostrar a linha de sucesso `✅ Dependências instaladas`.
3. `make up` (sobe LocalStack; aguarda health) — explicar que espera por varredura, não sleep.
4. `make test` — roda os 3 testes; explicar que `test-v9` demora ~2min. Mencionar `make test-v7/-v8/-v9` individuais (existem no Makefile).
5. Inspecionar recursos: bloco `export AWS_ENDPOINT_URL=...` + `aws --endpoint-url ... sns list-topics`.
6. `make clean` ao terminar.

> ⚠️ **Pegadinha** sobre ativar o venv / o `make` já usa `.venv/bin/python3`.
Rodapé: Anterior = `pre-requisitos.md`; Próximo = `../01-fundamentos/1-serverless-e-lambda.md`.

- [ ] **Step 4: Verificar que os comandos citados existem no Makefile**

Run: `grep -E '^(install|up|test|test-v7|test-v8|test-v9|clean):' Makefile`
Expected: lista os alvos (confirma que a página não inventou comandos).

- [ ] **Step 5: Commit**

```bash
git add docs/00-comece-aqui/
git commit -m "docs(portal): etapa 'comece aqui' (pré-requisitos e setup local)"
```

---

### Task 4: Fundamentos — parte 1 (serverless + orientado a eventos)

**Files:**
- Create: `docs/01-fundamentos/1-serverless-e-lambda.md`
- Create: `docs/01-fundamentos/2-orientado-a-eventos.md`

- [ ] **Step 1: Escrever `1-serverless-e-lambda.md`**

Conteúdo conceitual (sem AWS-specifics ainda do domínio):
- O que é serverless (você não gerencia servidor; o provedor executa sua função sob demanda).
- O que é uma função Lambda: assinatura `lambda_handler(event, context)`. Mostrar **verbatim** o handler do produtor como primeiro contato com a forma:

```bash
sed -n '/^def lambda_handler/,/return pedido/p' src/U1V7_fanout/produtor.py
```
Cole o trecho extraído num bloco ```python.
- Cold start vs warm: por que clientes boto3 são criados **fora** do handler. Mostrar verbatim as linhas de criação do cliente + comentário:

```bash
sed -n '/Clientes criados fora do handler/,/TOPIC_ARN = /p' src/U1V7_fanout/produtor.py
```
- `> 📌 Conceito` ligando ao glossário (link para `../glossario.md`).
Rodapé: Anterior = `../00-comece-aqui/setup-local.md`; Próximo = `2-orientado-a-eventos.md`.

- [ ] **Step 2: Escrever `2-orientado-a-eventos.md`**

- O que é arquitetura orientada a eventos: produtor publica um fato; consumidores reagem; não se conhecem.
- Acoplado vs desacoplado (o contraste produtor-chama-3-filas vs produtor-publica-1-tópico). Pode reaproveitar a ideia do roteiro antigo U1V7, mas **sem** pseudonomes — descrição conceitual + `sns.publish(...)` real (1 linha) do `produtor.py`.
- Push vs pull; por que filas absorvem picos.
- Antecipa as 3 garantias que as demos exploram: fan-out, at-least-once/idempotência, DLQ (1 linha cada, com link para a demo correspondente).
Rodapé: Anterior = `1-serverless-e-lambda.md`; Próximo = `3-os-quatro-servicos.md`.

- [ ] **Step 3: Verificar fidelidade**

Run: `grep -q "boto3.client(\"sns\"" docs/01-fundamentos/1-serverless-e-lambda.md && echo OK`
Expected: `OK` (o trecho real do cliente SNS foi colado).

- [ ] **Step 4: Commit**

```bash
git add docs/01-fundamentos/1-serverless-e-lambda.md docs/01-fundamentos/2-orientado-a-eventos.md
git commit -m "docs(portal): fundamentos 1-2 (serverless/Lambda e orientado a eventos)"
```

---

### Task 5: Fundamentos — parte 2 (os 4 serviços + como ler o código)

**Files:**
- Create: `docs/01-fundamentos/3-os-quatro-servicos.md`
- Create: `docs/01-fundamentos/4-como-ler-o-codigo.md`

- [ ] **Step 1: Escrever `3-os-quatro-servicos.md`**

Uma seção por serviço, cada uma respondendo "o que é / qual papel nas demos":
- **SNS** — tópico pub/sub; produtores publicam, assinantes recebem cópia.
- **SQS** — filas; garantia **at-least-once** (a mesma mensagem pode chegar 2×) — gancho para U1V8.
- **Lambda** — computação por evento (já visto no fundamento 1).
- **DynamoDB** — tabela chave-valor; usada como tabela de controle de idempotência; TTL.
- `> 📌 Conceito` **ARN vs URL** (a distinção do glossário) e **ESM** (Event Source Mapping). Todas as siglas linkam para `../glossario.md`, sem redefinir.
Rodapé: Anterior = `2-orientado-a-eventos.md`; Próximo = `4-como-ler-o-codigo.md`.

- [ ] **Step 2: Escrever `4-como-ler-o-codigo.md`**

Tour do repositório para o aluno saber **onde** está cada coisa:
- Árvore `src/ infra/ tests/` (reaproveitar a árvore da seção "Estrutura do projeto" do README).
- Padrão `endpoint_url=os.environ.get("AWS_ENDPOINT_URL")`: explicar que sem a variável o boto3 usa a AWS real — zero mudança de código. Mostrar verbatim 1 linha de criação de cliente.
- LocalStack ↔ AWS Real: a mesma stack roda nos dois (link para ADR-002/003 em `../03-aprofundar/decisoes-adr.md`).
- Onde a infra mora: `infra/template.yaml` declara tudo; `tests/aws_builder.py` constrói o equivalente para os testes (link para `../03-aprofundar/aws-builder.md`).
- `> 💡 Dica`: "ao ler cada demo, abra o arquivo `src/` ao lado — o portal mostra o mesmo código".
Rodapé: Anterior = `3-os-quatro-servicos.md`; Próximo = `../02-demos/u1v7-fan-out.md`.

- [ ] **Step 3: Commit**

```bash
git add docs/01-fundamentos/3-os-quatro-servicos.md docs/01-fundamentos/4-como-ler-o-codigo.md
git commit -m "docs(portal): fundamentos 3-4 (os quatro serviços e como ler o código)"
```

---

### Task 6: Demo U1V7 — Fan-out

**Files:**
- Create: `docs/02-demos/u1v7-fan-out.md`
- Lê (verbatim): `src/U1V7_fanout/produtor.py`, `src/U1V7_fanout/estoque.py`, `src/U1V7_fanout/notificacao.py`, `infra/template.yaml`, `docs/architecture/README.md`

- [ ] **Step 1: Extrair os trechos reais**

```bash
cat src/U1V7_fanout/produtor.py
cat src/U1V7_fanout/estoque.py
cat src/U1V7_fanout/notificacao.py
sed -n '/AQUI mora o fan-out/,/aws:SourceArn: !Ref TopicoPedidos/p' infra/template.yaml   # assinaturas + QueuePolicy
sed -n '/## U1V7/,/## U1V8/p' docs/architecture/README.md                                 # diagrama mermaid
```

- [ ] **Step 2: Escrever a aula seguindo a anatomia fixa**

1. **Objetivo** + pré-requisitos (fundamentos 1–4).
2. **O problema**: produtor acoplado a N filas.
3. **Solução em diagrama**: colar o bloco ```mermaid de `architecture/README.md` (seção U1V7).
4. **Código real explicado**: `produtor.py` (verbatim) — destacar o **único** `_sns.publish(...)`; depois `estoque.py` e `notificacao.py` (verbatim) — consumidores independentes.
5. **Infraestrutura**: colar verbatim as 2 `AWS::SNS::Subscription` com `RawMessageDelivery: true` e a `PoliticaFilas` (`QueuePolicy`). `> ⚠️ Pegadinha`: sem a QueuePolicy o SNS não consegue entregar no SQS.
6. **Rodar e observar**: `make test-v7`; o que o teste valida (mensagem chega nas duas filas).
7. **Pegadinhas**: o fan-out NÃO está no código do produtor — está nas assinaturas. `RawMessageDelivery` (JSON puro vs envelope SNS).
8. **Checklist** (adaptar do roteiro antigo, com nomes reais) + link para `../exercicios.md#u1v7`.
Rodapé: Anterior = `../01-fundamentos/4-como-ler-o-codigo.md`; Próximo = `u1v8-idempotencia.md`.

- [ ] **Step 3: Verificar fidelidade (nomes reais, não pseudonomes)**

Run:
```bash
grep -q "RawMessageDelivery" docs/02-demos/u1v7-fan-out.md && \
! grep -q "EntregaMensagemPura" docs/02-demos/u1v7-fan-out.md && echo OK
```
Expected: `OK` (usa o nome real, não o pseudonome).

- [ ] **Step 4: Commit**

```bash
git add docs/02-demos/u1v7-fan-out.md
git commit -m "docs(portal): aula U1V7 fan-out (alinhada ao código real)"
```

---

### Task 7: Demo U1V8 — Idempotência

**Files:**
- Create: `docs/02-demos/u1v8-idempotencia.md`
- Lê (verbatim): `src/U1V8_idempotencia/processa_pedido.py`, `infra/template.yaml`, `docs/architecture/README.md`, `tests/test_U1V8_idempotencia.py`

- [ ] **Step 1: Extrair os trechos reais**

```bash
cat src/U1V8_idempotencia/processa_pedido.py
sed -n '/TabelaMensagensProcessadas/,/DynamoDBCrudPolicy/p' infra/template.yaml
sed -n '/## U1V8/,/## U1V9/p' docs/architecture/README.md
```

- [ ] **Step 2: Escrever a aula seguindo a anatomia fixa**

1. **Objetivo** + pré-requisitos.
2. **O problema**: SQS é **at-least-once** → cobrança/efeito duplicado.
3. **Solução em diagrama**: bloco ```mermaid de sequência (seção U1V8 de `architecture/README.md`).
4. **Código real explicado**: `processa_pedido.py` verbatim. Explicar `lambda_handler` → `_reivindicar()` → `_processar_pedido()`. Destacar o **claim antes do efeito colateral**.
5. **A pegadinha da race condition**: colar verbatim a docstring de `_reivindicar` que mostra o cenário `GetItem + PutItem` (invocações A/B) e por que o `PutItem` condicional atômico (`ConditionExpression="attribute_not_exists(messageId)"`) resolve.
6. **Infraestrutura**: colar a `TabelaMensagensProcessadas` (chave `messageId`, TTL `expira_em`).
7. **Rodar e observar**: `make test-v8`; mencionar os 4 testes (primeira entrega registra; segunda é ignorada; TTL presente; duplicata não vira FunctionError).
8. **Pegadinhas**: por que a `ConditionalCheckFailedException` **não pode vazar** (senão o SQS retentaria infinitamente → DLQ). Descartar duplicata em silêncio é o correto.
9. **Checklist** + link para `../exercicios.md#u1v8`.
Rodapé: Anterior = `u1v7-fan-out.md`; Próximo = `u1v9-dlq.md`.

- [ ] **Step 3: Verificar fidelidade**

Run:
```bash
grep -q 'attribute_not_exists(messageId)' docs/02-demos/u1v8-idempotencia.md && \
grep -q 'ConditionalCheckFailedException' docs/02-demos/u1v8-idempotencia.md && \
! grep -q 'ExpressionoCondicao' docs/02-demos/u1v8-idempotencia.md && echo OK
```
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add docs/02-demos/u1v8-idempotencia.md
git commit -m "docs(portal): aula U1V8 idempotência (alinhada ao código real)"
```

---

### Task 8: Demo U1V9 — DLQ

**Files:**
- Create: `docs/02-demos/u1v9-dlq.md`
- Lê (verbatim): `src/U1V9_dlq/consumidora_b.py`, `infra/template.yaml`, `docs/architecture/README.md`

- [ ] **Step 1: Extrair os trechos reais**

```bash
cat src/U1V9_dlq/consumidora_b.py
sed -n '/FilaEstoque:/,/maxReceiveCount: 3/p' infra/template.yaml       # RedrivePolicy na fila principal
sed -n '/FilaEstoqueDLQ:/,/BatchSize: 1/p' infra/template.yaml          # DLQ + consumidora
sed -n '/## U1V9/,/## Componentes/p' docs/architecture/README.md        # stateDiagram mermaid
```

- [ ] **Step 2: Escrever a aula seguindo a anatomia fixa**

1. **Objetivo** + pré-requisitos.
2. **O problema**: mensagem "venenosa" que falha sempre → trava a fila.
3. **Solução em diagrama**: bloco ```mermaid `stateDiagram` (seção U1V9 de `architecture/README.md`).
4. **Código real explicado**: `consumidora_b.py` verbatim — a `raise RuntimeError` proposital quando `defeituoso`. Explicar: deixar a exceção **escapar do handler** sinaliza ao SQS que a mensagem não foi processada.
5. **Infraestrutura**: colar a `FilaEstoque` com `RedrivePolicy`/`maxReceiveCount: 3` e a `FilaEstoqueDLQ` (retenção 14 dias). `> 📌` "DLQ não é tipo especial — é uma fila comum apontada por RedrivePolicy" (do glossário).
6. **Rodar e observar**: `make test-v9` (~2min — explicar os 3 ciclos de retry). Validações: defeituosa vai pra DLQ; saudável processa; fila principal esvazia.
7. **Fluxo detalhado**: recepção → exceção → visibility timeout → volta → após `maxReceiveCount`, vai pra DLQ.
8. **Pegadinhas**: fingir sucesso (`return 200` no except) **perde** a mensagem; deixar vazar é o correto. Fluxo de correção (corrigir código → reenviar da DLQ) — citar o comentário do próprio arquivo.
9. **Checklist** + link para `../exercicios.md#u1v9`.
Rodapé: Anterior = `u1v8-idempotencia.md`; Próximo = `../03-aprofundar/arquitetura.md`.

- [ ] **Step 3: Verificar fidelidade**

Run:
```bash
grep -q 'RedrivePolicy' docs/02-demos/u1v9-dlq.md && \
grep -q 'maxReceiveCount' docs/02-demos/u1v9-dlq.md && \
grep -q 'RuntimeError' docs/02-demos/u1v9-dlq.md && \
! grep -q 'PolíticaReenvio' docs/02-demos/u1v9-dlq.md && echo OK
```
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add docs/02-demos/u1v9-dlq.md
git commit -m "docs(portal): aula U1V9 DLQ (alinhada ao código real)"
```

---

### Task 9: Aprofundar + exercícios + remover artefatos antigos

**Files:**
- Create: `docs/03-aprofundar/arquitetura.md`
- Create: `docs/03-aprofundar/aws-builder.md`
- Create: `docs/03-aprofundar/decisoes-adr.md`
- Create: `docs/exercicios.md`
- Delete: `docs/aws_builder_walkthrough.md`, `docs/roteiros/` (pasta inteira)

- [ ] **Step 1: `03-aprofundar/arquitetura.md`**

Página-ponte: 1 parágrafo explicando que aqui está a visão arquitetural completa, + link para `../architecture/README.md` (diagramas C4, fluxo, sequência) e a tabela "Componentes e Responsabilidades". Não duplicar os diagramas — linkar. (Os diagramas individuais já foram usados nas demos.)
Rodapé: Anterior = `../02-demos/u1v9-dlq.md`; Próximo = `aws-builder.md`.

- [ ] **Step 2: `03-aprofundar/aws-builder.md` (migração)**

Run: `cat docs/aws_builder_walkthrough.md`
Mover o conteúdo para o novo arquivo, **atualizando**: trocar qualquer menção a "MFE" por "ESM" (o código usa ESM); garantir que o glossário referenciado aponte para `../glossario.md` em vez de reproduzir. Adicionar rodapé de trilha (Anterior = `arquitetura.md`; Próximo = `decisoes-adr.md`).

- [ ] **Step 3: `03-aprofundar/decisoes-adr.md`**

Página-ponte: lista os 3 ADRs com 1 linha cada e link para cada arquivo em `../architecture/adrs/` (ADR-001 boto3, ADR-002 LocalStack, ADR-003 endpoint-url).
Run para confirmar os nomes: `ls docs/architecture/adrs/`
Rodapé: Anterior = `aws-builder.md`; Próximo = `../exercicios.md`.

- [ ] **Step 4: `docs/exercicios.md`**

Três seções com âncoras `#u1v7`, `#u1v8`, `#u1v9` (linkadas pelos checklists das demos). Cada uma com 2–3 desafios práticos de mexer no código e observar, ex.:
- U1V7: adicionar uma terceira fila (analytics) e assiná-la; observar o fan-out sem tocar no produtor.
- U1V8: comentar o `ConditionExpression` e ver a duplicata escapar no teste.
- U1V9: mudar `maxReceiveCount` para 1; remover o bloco `if pedido.get("defeituoso")` e reenviar da DLQ.
Cada desafio: objetivo, passos, resultado esperado. Tom: "experimente e observe".
Rodapé: Anterior = `03-aprofundar/decisoes-adr.md`; Próximo = `glossario.md`.

- [ ] **Step 5: Remover artefatos antigos**

```bash
git rm docs/aws_builder_walkthrough.md
rm -rf docs/roteiros   # não versionada (estava como untracked)
```

- [ ] **Step 6: Adicionar rodapé ao glossário**

Editar `docs/glossario.md`: adicionar rodapé de trilha (Anterior = `exercicios.md`; sem Próximo). Índice = `index.md`.

- [ ] **Step 7: Commit**

```bash
git add docs/03-aprofundar/ docs/exercicios.md docs/glossario.md
git add -A docs/
git commit -m "docs(portal): aprofundar, exercícios e remoção dos roteiros antigos"
```

---

### Task 10: README + verificação final de integridade

**Files:**
- Modify: `README.md` (seção Referências e ponteiro para o portal)

- [ ] **Step 1: Atualizar `README.md`**

- No topo, logo após a descrição, adicionar: `> 📚 **Portal de documentação:** comece por docs/index.md — trilha didática do zero ao entendimento do código.`
- Na seção **Referências**: substituir os links para `docs/roteiros/*` (que não existem mais) pelos novos: `docs/02-demos/u1v7-fan-out.md`, `u1v8-idempotencia.md`, `u1v9-dlq.md`; trocar `docs/aws_builder_walkthrough.md` por `docs/03-aprofundar/aws-builder.md`. Manter os links de architecture/ e adrs/.

Run para localizar os links a trocar: `grep -n "roteiros\|aws_builder_walkthrough" README.md`

- [ ] **Step 2: Verificação final de links (deve passar 100%)**

Run: `VERIFICA_LINKS`
Expected: `OK: nenhum link quebrado`

- [ ] **Step 3: Verificar que nenhum pseudonome sobrou no portal**

Run:
```bash
grep -rn "EntregaMensagemPura\|ExpressionoCondicao\|VerificacaoCondicionalFalhou\|PolíticaReenvio\|maximo_recebimentos\|gerenciador_lambda\|ErroDeExecucao" docs/ ; echo "exit=$?"
```
Expected: nenhuma linha; `exit=1` do grep (nada encontrado). Se aparecer algo, corrigir para o nome real e re-rodar.

- [ ] **Step 4: Verificar a ordem da trilha (rodapés encadeiam)**

Run: `grep -rl "Próximo:" docs/ | wc -l`
Expected: 14 (todas as páginas da trilha menos o glossário têm "Próximo").
Conferir manualmente que cada "Próximo" de uma página é o "Anterior" da seguinte, conforme "Ordem da trilha".

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs(portal): README aponta para o portal e corrige referências"
```

---

## Self-Review (preenchido)

**1. Spec coverage:**
- Markdown puro, sem build → respeitado (só Python para verificação de links). ✔
- Trilha completa (fundamentos + demos + aprofundar + glossário + exercícios) → Tasks 2–9. ✔
- Alinhado ao código real → regra de ouro + verificações de fidelidade em Tasks 6/7/8/10. ✔
- Estrutura de pastas da spec → Task 1 + arquivos nas tasks seguintes. ✔
- Anatomia fixa das aulas → Tasks 6/7/8 replicam os 8 itens. ✔
- Glossário único = `aws_builder.py` → Task 1. ✔
- Tratamento de arquivos existentes (roteiros removidos, walkthrough migrado, architecture/adrs mantidos, README editado) → Tasks 9 e 10. ✔
- Convenções (voz, caixas, links relativos, siglas via glossário) → regras transversais. ✔
- Critérios de sucesso (links ok, sem siglas órfãs, sem pseudonomes, README aponta) → Task 10 verifica. ✔

**2. Placeholder scan:** sem "TBD/TODO". Os trechos de código são extraídos verbatim dos arquivos reais via `sed/cat` (mais seguro que redigitar). ✔

**3. Type consistency:** caminhos de arquivo e a "Ordem da trilha" são consistentes entre tasks e rodapés; âncoras de exercícios (`#u1v7/#u1v8/#u1v9`) batem com os links nos checklists das demos. ✔
