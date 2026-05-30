# Pré-requisitos

Antes de rodar qualquer demo você precisa ter as ferramentas abaixo instaladas.
Não precisa ser especialista em AWS — a trilha constrói esse conhecimento ao longo do caminho.

## Ferramentas necessárias

| Ferramenta | Versão | Para quê |
|---|---|---|
| Docker | recente | Subir o LocalStack |
| Python | 3.12 | Rodar os testes |
| make | qualquer | Atalhos de comando (pré-instalado no Mac via Xcode CLI Tools) |
| AWS CLI v2 | recente | Inspecionar recursos via terminal |
| SAM CLI | recente | Deploy na AWS Real (opcional) |

> `boto3` e `pytest` são instalados automaticamente pelo `make install` via `pip install -r requirements.txt` — você não precisa instalá-los manualmente.

### Mac: nota sobre o `make`

**Mac:** `make` já vem com o Xcode Command Line Tools. Se não tiver instalado: `xcode-select --install`. Para verificar: `make --version`.

## Conceitos que ajudam (mas não são obrigatórios)

Você vai se sentir mais confortável se já tiver noção de:

- **Linha de comando** — navegar em diretórios, rodar comandos no terminal.
- **Python básico** — ler e entender funções simples; você não precisará escrever código do zero.
- **JSON** — os eventos AWS são objetos JSON; saber ler o formato é suficiente.

Não sabe tudo isso ainda? Tudo bem. Os roteiros explicam cada passo. Você aprende fazendo.

---

⬅️ [Anterior: Índice](../index.md) · 📑 [Índice](../index.md) · [Próximo: Setup local](setup-local.md) ➡️
