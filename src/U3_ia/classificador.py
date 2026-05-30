"""Classificador de eventos com IA (U3V9).

Recebe e-mails de suporte via SQS, classifica com a Anthropic (Claude Haiku),
cacheia o resultado em DynamoDB (evita custo em textos repetidos) e roteia
para a fila de prioridade correspondente.
"""
import hashlib
import json
import os
import time

import boto3

MODELO = "claude-haiku-4-5"
TTL_SEGUNDOS = 24 * 3600

# Override de cliente LLM para testes (injeção). Em produção fica None.
_override_llm = None


def usar_cliente_llm(cliente) -> None:
    """Injeta um cliente LLM (usado nos testes). Passe None para usar o real."""
    global _override_llm
    _override_llm = cliente


def _cliente_llm():
    if _override_llm is not None:
        return _override_llm
    import anthropic
    return anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente


def _sqs():
    return boto3.client("sqs", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))


def _tabela_cache():
    dynamodb = boto3.resource("dynamodb", endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
    return dynamodb.Table(os.environ.get("TABELA_CACHE", "classificacoes"))


def _url_fila(sqs, nome: str) -> str:
    return sqs.get_queue_url(QueueName=nome)["QueueUrl"]


def classificar(texto: str, cliente=None) -> dict:
    """Chama o LLM e devolve {'prioridade': ..., 'categoria': ...} validado."""
    cliente = cliente or _cliente_llm()
    resp = cliente.messages.create(
        model=MODELO,
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": (
                "Classifique o e-mail de suporte abaixo. Responda APENAS um JSON "
                'no formato {"prioridade": "alta|baixa", "categoria": "tecnico|comercial"}.\n\n'
                f"E-mail: {texto}"
            ),
        }],
    )
    dados = json.loads(resp.content[0].text)
    return {"prioridade": dados["prioridade"], "categoria": dados["categoria"]}


def lambda_handler(event, context):
    sqs = _sqs()
    tabela = _tabela_cache()
    for record in event["Records"]:
        texto = record["body"]
        hash_texto = hashlib.sha256(texto.encode()).hexdigest()

        cacheado = tabela.get_item(Key={"hash_texto": hash_texto}).get("Item")
        if cacheado:
            classificacao = {"prioridade": cacheado["prioridade"], "categoria": cacheado["categoria"]}
        else:
            try:
                classificacao = classificar(texto)
            except Exception as e:  # JSON inválido, erro de API, etc.
                print(f"[CLASSIFICADOR] Falha ao classificar: {e}")
                sqs.send_message(QueueUrl=_url_fila(sqs, "sem-classificacao"), MessageBody=texto)
                continue
            tabela.put_item(Item={
                "hash_texto": hash_texto,
                "prioridade": classificacao["prioridade"],
                "categoria": classificacao["categoria"],
                "expira_em": int(time.time()) + TTL_SEGUNDOS,
            })

        fila = "alta-prioridade" if classificacao["prioridade"] == "alta" else "baixa-prioridade"
        sqs.send_message(QueueUrl=_url_fila(sqs, fila), MessageBody=texto)
