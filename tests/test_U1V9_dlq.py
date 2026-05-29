"""
Testes da Demo U1V9 — Dead-Letter Queue (DLQ) e Resiliência

O que estes testes verificam:
    Uma mensagem que sempre falha (poison message / mensagem envenenada)
    é roteada para a DLQ após maxReceiveCount tentativas, sem bloquear
    o processamento das mensagens saudáveis que vêm depois.

Como estes testes funcionam:
    Usam event source mapping real (SQS → Lambda) para observar o
    comportamento do ciclo de retry. Não usam mocks — o SQS de verdade
    (via LocalStack) executa as tentativas com visibility timeout.

Por que estes testes são lentos (~90s cada):
    Cada teste aguarda 3 tentativas × 10s de visibility timeout antes
    de a mensagem ser roteada para a DLQ. Isso é intencional — estamos
    observando o comportamento real, não simulando.

Pré-condição: `make up` (LocalStack rodando).
"""
import json
import uuid

import pytest

from tests.helpers import deploy_lambda, make_client, wait_until, assert_never

# ── Constantes ────────────────────────────────────────────────────────────────

NOME_DA_FUNCAO = "consumidora-b"
CAMINHO_DO_HANDLER = "src/U1V9_dlq/consumidora_b.py"
NOME_DA_FILA_PRINCIPAL = "fila-estoque-v9"
NOME_DA_FILA_MORTA = "fila-estoque-v9-dlq"

# Visibility timeout curto para agilizar os testes (produção usaria 30s ou mais).
# Controla o intervalo entre as tentativas de reprocessamento.
TEMPO_DE_VISIBILIDADE_EM_SEGUNDOS = 10

# ── Infraestrutura dos testes (fixtures) ──────────────────────────────────────


@pytest.fixture(scope="module")
def fila_com_dlq(sqs) -> dict:
    """
    Cria a fila principal com a política de reenvio (RedrivePolicy) vinculada
    à fila morta (DLQ).

    maxReceiveCount=3: a mensagem é roteada para a DLQ na 4ª recepção,
    após falhar nas 3 primeiras tentativas.

    A RedrivePolicy fica na fila PRINCIPAL — não na DLQ.
    A DLQ é passiva: ela só recebe o que a fila principal rejeita.
    """
    url_fila_morta = sqs.create_queue(QueueName=NOME_DA_FILA_MORTA)["QueueUrl"]
    arn_fila_morta = sqs.get_queue_attributes(
        QueueUrl=url_fila_morta, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    politica_de_reenvio = json.dumps({
        "deadLetterTargetArn": arn_fila_morta,
        "maxReceiveCount": "3",
    })

    url_fila_principal = sqs.create_queue(
        QueueName=NOME_DA_FILA_PRINCIPAL,
        Attributes={
            "VisibilityTimeout": str(TEMPO_DE_VISIBILIDADE_EM_SEGUNDOS),
            "RedrivePolicy": politica_de_reenvio,
        },
    )["QueueUrl"]

    return {
        "url_fila_principal": url_fila_principal,
        "url_fila_morta": url_fila_morta,
    }


@pytest.fixture(scope="module")
def funcao_com_dlq(lam, fila_com_dlq) -> str:
    """
    Faz o deploy da consumidora_b.py (com falha proposital ativa) e
    vincula a fila principal como gatilho via event source mapping.
    """
    deploy_lambda(
        lambda_client=lam,
        function_name=NOME_DA_FUNCAO,
        source_path=CAMINHO_DO_HANDLER,
        handler="consumidora_b.lambda_handler",
    )
    _vincular_fila_a_lambda(lam, NOME_DA_FUNCAO, fila_com_dlq["url_fila_principal"])
    return NOME_DA_FUNCAO


# ── Funções auxiliares ────────────────────────────────────────────────────────


def _obter_arn_da_fila(url_da_fila: str) -> str:
    """Retorna o ARN de uma fila SQS a partir da URL."""
    cliente_sqs = make_client("sqs")
    return cliente_sqs.get_queue_attributes(
        QueueUrl=url_da_fila, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]


def _vincular_fila_a_lambda(lam, nome_da_funcao: str, url_da_fila: str) -> None:
    """
    Cria o Event Source Mapping: o SQS passa a chamar a Lambda
    automaticamente quando mensagens chegam na fila.
    BatchSize=1: cada invocação processa uma mensagem por vez,
    facilitando a observação do ciclo de retry nos logs.
    """
    arn_da_fila = _obter_arn_da_fila(url_da_fila)
    try:
        lam.create_event_source_mapping(
            EventSourceArn=arn_da_fila,
            FunctionName=nome_da_funcao,
            BatchSize=1,
            Enabled=True,
        )
    except lam.exceptions.ResourceConflictException:
        pass  # gatilho já existe — ok em execuções repetidas


# ── Testes ────────────────────────────────────────────────────────────────────


@pytest.mark.timeout(120)
def test_mensagem_envenenada_e_roteada_para_dlq_apos_tres_falhas(sqs, fila_com_dlq, funcao_com_dlq):
    """
    Uma mensagem com "defeituoso": true deve ser roteada para a DLQ
    após 3 tentativas de processamento malsucedidas.

    Fluxo esperado:
        Fila → Lambda → RuntimeError → mensagem volta (visibility timeout)
        Fila → Lambda → RuntimeError → mensagem volta
        Fila → Lambda → RuntimeError → mensagem volta
        Fila → DLQ (4ª recepção, maxReceiveCount atingido)

    A poison message sai do caminho — a fila principal fica livre para
    processar as mensagens que vêm depois.
    """
    identificador_do_produto = f"SKU-{uuid.uuid4().hex[:8].upper()}"

    sqs.send_message(
        QueueUrl=fila_com_dlq["url_fila_principal"],
        MessageBody=json.dumps({
            "sku": identificador_do_produto,
            "qtd": 1,
            "defeituoso": True,
        }),
    )

    def mensagem_chegou_na_fila_morta():
        resposta = sqs.receive_message(
            QueueUrl=fila_com_dlq["url_fila_morta"],
            MaxNumberOfMessages=1,
            VisibilityTimeout=5,
        )
        return any(
            identificador_do_produto in m["Body"]
            for m in resposta.get("Messages", [])
        )

    wait_until(
        mensagem_chegou_na_fila_morta,
        timeout=90,
        interval=2,
        message="a mensagem envenenada não chegou na DLQ no tempo esperado",
    )


@pytest.mark.timeout(120)
def test_dlq_preserva_o_payload_original_intacto(sqs, fila_com_dlq, funcao_com_dlq):
    """
    O payload que chega na DLQ deve ser idêntico ao que foi enviado
    originalmente — nenhum campo alterado, nenhum dado perdido.

    Isso é fundamental: a DLQ não é uma lixeira. É um repositório de
    mensagens para investigação e reprocessamento posterior, quando
    o problema que causou a falha for corrigido.
    """
    identificador_do_produto = f"SKU-{uuid.uuid4().hex[:8].upper()}"
    payload_original = {
        "sku": identificador_do_produto,
        "qtd": 5,
        "defeituoso": True,
        "origem": "teste-v9",
    }

    sqs.send_message(
        QueueUrl=fila_com_dlq["url_fila_principal"],
        MessageBody=json.dumps(payload_original),
    )

    payload_recebido_na_dlq = None

    def encontrar_mensagem_na_fila_morta():
        nonlocal payload_recebido_na_dlq
        resposta = sqs.receive_message(
            QueueUrl=fila_com_dlq["url_fila_morta"],
            MaxNumberOfMessages=10,
            VisibilityTimeout=5,
        )
        for mensagem in resposta.get("Messages", []):
            if identificador_do_produto in mensagem["Body"]:
                payload_recebido_na_dlq = json.loads(mensagem["Body"])
                return True
        return False

    wait_until(
        encontrar_mensagem_na_fila_morta,
        timeout=90,
        interval=2,
        message="mensagem não chegou na DLQ para validar o payload",
    )

    assert payload_recebido_na_dlq["sku"] == identificador_do_produto
    assert payload_recebido_na_dlq["qtd"] == 5
    assert payload_recebido_na_dlq["origem"] == "teste-v9"


@pytest.mark.timeout(30)
def test_mensagem_valida_nao_e_enviada_para_dlq(sqs, fila_com_dlq, funcao_com_dlq):
    """
    Uma mensagem sem "defeituoso" deve ser processada normalmente
    e NÃO deve aparecer na DLQ.

    Demonstra que a DLQ isola apenas as mensagens problemáticas.
    O fluxo normal continua funcionando sem interrupção.
    """
    identificador_do_produto = f"SKU-{uuid.uuid4().hex[:8].upper()}"

    sqs.send_message(
        QueueUrl=fila_com_dlq["url_fila_principal"],
        MessageBody=json.dumps({
            "sku": identificador_do_produto,
            "qtd": 3,
            # sem "defeituoso" — mensagem saudável
        }),
    )

    def mensagem_saudavel_esta_na_fila_morta():
        resposta = sqs.receive_message(
            QueueUrl=fila_com_dlq["url_fila_morta"],
            MaxNumberOfMessages=10,
        )
        return any(
            identificador_do_produto in m["Body"]
            for m in resposta.get("Messages", [])
        )

    assert_never(
        mensagem_saudavel_esta_na_fila_morta,
        duration=15,
        message="mensagem saudável não deveria ir para a fila morta (DLQ)",
    )
