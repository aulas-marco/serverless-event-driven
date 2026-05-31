# Pré-requisitos

Antes de rodar qualquer demo da Unidade 2 você precisa ter as ferramentas abaixo instaladas.
Não precisa ter experiência com Event Sourcing — a trilha constrói esse conhecimento ao longo do caminho.

## Ferramentas necessárias

| Ferramenta | Versão | Para quê |
|---|---|---|
| Docker | recente | Subir o LocalStack |
| Python | 3.12 ou superior | Rodar os testes (o `make install` usa 3.13 se disponível; o runtime Lambda no `template.yaml` é 3.12) |
| make | qualquer | Atalhos de comando (pré-instalado no Mac via Xcode CLI Tools) |
| AWS CLI v2 | recente | Inspecionar tabelas DynamoDB via terminal |
| SAM CLI | recente | Deploy na AWS real (opcional) |

> `boto3` e `pytest` são instalados automaticamente pelo `make install` via `pip install -r requirements.txt` — você não precisa instalá-los manualmente.

### Mac: nota sobre o `make`

**Mac:** `make` já vem com o Xcode Command Line Tools. Se não tiver instalado: `xcode-select --install`. Para verificar: `make --version`.

## Conceitos que ajudam (mas não são obrigatórios)

Você vai se sentir mais confortável se já tiver noção de:

- **Linha de comando** — navegar em diretórios, rodar comandos no terminal.
- **Python básico** — ler e entender funções simples; você não precisará escrever código do zero.
- **JSON** — os eventos são objetos JSON; saber ler o formato é suficiente.
- **DynamoDB básico** — saber o que é chave primária e `PutItem`; a trilha explica o restante.

Completou a Unidade 1? Você já tem todas as ferramentas instaladas e o LocalStack configurado — pode ir direto para o [Setup local](setup-local.md).

Não sabe tudo isso ainda? Tudo bem. Os roteiros explicam cada passo. Você aprende fazendo.

---

⬅️ [Anterior: Índice](../index.md) · 📑 [Índice](../index.md) · [Próximo: Setup local](setup-local.md) ➡️
