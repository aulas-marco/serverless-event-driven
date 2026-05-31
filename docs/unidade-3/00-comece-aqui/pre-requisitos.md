# Pré-requisitos

Antes de rodar qualquer demo da Unidade 3 você precisa ter as ferramentas abaixo instaladas.
Não precisa ser especialista em AWS ou Kafka — a trilha constrói esse conhecimento ao longo do caminho.

## Ferramentas necessárias

| Ferramenta | Versão | Para quê |
|---|---|---|
| Docker | recente | Subir o LocalStack, o Kafka (KRaft) e o Kafka UI |
| Python | 3.12 ou 3.13 | Rodar os testes (o `make install` usa 3.13 se disponível; o runtime Lambda no `template.yaml` é 3.12) |
| make | qualquer | Atalhos de comando (pré-instalado no Mac via Xcode CLI Tools) |
| AWS CLI v2 | recente | Inspecionar recursos via terminal |
| SAM CLI | recente | Deploy na AWS Real (opcional) |

> `boto3`, `pytest`, `confluent-kafka` e `anthropic` são instalados automaticamente pelo `make install` via `pip install -r requirements.txt` — você não precisa instalá-los manualmente.

### Mac: nota sobre o `make`

**Mac:** `make` já vem com o Xcode Command Line Tools. Se não tiver instalado: `xcode-select --install`. Para verificar: `make --version`.

---

## O que a Unidade 3 adiciona em relação às anteriores

A Unidade 3 usa dois serviços a mais além do LocalStack:

- **Kafka (KRaft)** — broker de mensagens persistente, sem ZooKeeper. Sobe via `docker compose` junto com o LocalStack.
- **Kafka UI** — interface web para inspecionar tópicos, partições e mensagens. Fica em <http://localhost:8080> após o `make up`.

Essas duas dependências são declaradas no `docker-compose.yml` do repositório e sobem automaticamente com o `make up` — não é necessário instalá-las separadamente.

### Bibliotecas Python extras

| Biblioteca | Por quê |
|---|---|
| `confluent-kafka` | Produtor e consumidor Kafka — demos U3V7 e U3V8 |
| `anthropic` | Cliente do modelo Claude (Haiku) — demo U3V9 |

> **Atenção U3V9:** A biblioteca `anthropic` e a chave `ANTHROPIC_API_KEY` são necessárias apenas para rodar a demo na **AWS Real**. Os testes da Unidade 3 injetam um cliente falso (`ClienteFake`) no lugar do cliente real — **rodam completamente offline, sem chave de API**.

---

## Conceitos que ajudam (mas não são obrigatórios)

Você vai se sentir mais confortável se já tiver noção de:

- **Linha de comando** — navegar em diretórios, rodar comandos no terminal.
- **Python básico** — ler e entender funções simples; você não precisará escrever código do zero.
- **JSON** — os eventos AWS e as mensagens Kafka são objetos JSON; saber ler o formato é suficiente.
- **Docker Compose** — saber o que é `docker compose up` e `docker compose down` é suficiente; você não precisará escrever arquivos Compose.

Não sabe tudo isso ainda? Tudo bem. Os roteiros explicam cada passo. Você aprende fazendo.

---

⬅️ [Anterior: Índice](../index.md) · 📑 [Índice](../index.md) · [Próximo: Setup local](setup-local.md) ➡️
