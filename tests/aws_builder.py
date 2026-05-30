"""
Construtores de infraestrutura AWS para os testes educacionais.

Cada classe encapsula a criação de recursos e expõe métodos de negócio.
Os testes não conhecem boto3 — apenas usam as interfaces aqui definidas.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Glossário de siglas — explicadas uma vez aqui, usadas em todo o projeto
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ARN   Amazon Resource Name — identificador único e global de qualquer
        recurso AWS. Formato: arn:aws:serviço:região:conta:recurso
        Exemplo:  arn:aws:sqs:us-east-1:000000000000:fila-estoque

  SNS   Simple Notification Service — serviço de mensageria pub/sub.
        Produtores publicam num tópico; cada assinante recebe uma cópia.

  SQS   Simple Queue Service — serviço de filas gerenciadas.
        Garantia de entrega: at-least-once (pelo menos uma vez).
        Isso significa que a mesma mensagem pode chegar mais de uma vez.

  URL   No contexto SQS: endereço HTTP único da fila, usado para enviar
        e receber mensagens. Diferente do ARN — a URL é o ponto de acesso;
        o ARN é o identificador do recurso.

  DLQ   Dead-Letter Queue (Fila de Mensagens Mortas) — fila SQS comum
        que recebe automaticamente as mensagens rejeitadas repetidamente
        por outra fila. Não existe um tipo especial "DLQ": o que faz uma
        fila ser DLQ é outra fila apontar para ela via RedrivePolicy.

  ESM   Event Source Mapping — vínculo que faz o SQS invocar uma Lambda
        automaticamente quando mensagens chegam na fila. Declarado uma
        vez; o SQS assume o papel de consumidor e dispara a Lambda.

  TTL   Time to Live — campo de timestamp (epoch Unix) que o DynamoDB
        usa para apagar registros automaticamente após a data configurada.
        Útil para tabelas de controle que não devem crescer indefinidamente.
"""
import json

from tests.helpers import deploy_lambda, drain_queue, wait_until


# ── Funções auxiliares privadas ───────────────────────────────────────────────


def _obter_arn_da_fila(sqs, url_da_fila: str) -> str:
    """
    Retorna o ARN de uma fila SQS a partir da URL.
    O ARN é necessário para criar assinaturas SNS e políticas de reenvio (DLQ).
    """
    return sqs.get_queue_attributes(
        QueueUrl=url_da_fila,
        AttributeNames=["QueueArn"],
    )["Attributes"]["QueueArn"]


def _aguardar_sem_conflito(lam, nome_da_funcao: str, timeout: float = 30.0) -> None:
    """
    Aguarda a função Lambda sair de estado de atualização pendente (LastUpdateStatus
    != InProgress), para que chamadas subsequentes como update_function_configuration
    não falhem com ResourceConflictException.
    """
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        cfg = lam.get_function(FunctionName=nome_da_funcao)["Configuration"]
        status = cfg.get("LastUpdateStatus", "Successful")
        if status != "InProgress":
            return
        time.sleep(1)
    raise TimeoutError(f"Lambda '{nome_da_funcao}' não saiu do estado InProgress (timeout={timeout}s)")


def _criar_esm(lam, nome_da_funcao: str, arn_da_fila: str) -> None:
    """
    Cria o Event Source Mapping (ESM): vínculo SQS → Lambda.
    BatchSize=1: cada invocação processa uma mensagem — facilita observar
    o ciclo de retry individualmente nos logs.
    """
    try:
        lam.create_event_source_mapping(
            EventSourceArn=arn_da_fila,
            FunctionName=nome_da_funcao,
            BatchSize=1,
            Enabled=True,
        )
    except lam.exceptions.ResourceConflictException:
        pass  # ESM já existe — ok em execuções repetidas


# ── U1V7 — Topologia Fan-out ──────────────────────────────────────────────────


class TopologiaFanout:
    """
    Monta a topologia SNS → 2 filas SQS e expõe operações de negócio.

    O fan-out está nas assinaturas: 1 publish no tópico gera entrega
    em CADA fila assinante. O código do produtor não menciona filas.

    Uso:
        topologia = TopologiaFanout(sqs, sns)
        topologia.publicar_pedido("P-001")
        assert topologia.pedido_chegou_nas_duas_filas("P-001")
    """

    NOME_DO_TOPICO = "pedidos"
    NOME_DA_FILA_ESTOQUE = "fila-estoque"
    NOME_DA_FILA_NOTIFICACAO = "fila-notificacao"

    def __init__(self, sqs, sns):
        self._sqs = sqs
        self._sns = sns

        # ARN do tópico — ponto único de publicação
        self.arn_do_topico = sns.create_topic(Name=self.NOME_DO_TOPICO)["TopicArn"]

        # URLs das filas — endereços de acesso para enviar/receber mensagens
        self.url_fila_estoque = sqs.create_queue(
            QueueName=self.NOME_DA_FILA_ESTOQUE
        )["QueueUrl"]
        self.url_fila_notificacao = sqs.create_queue(
            QueueName=self.NOME_DA_FILA_NOTIFICACAO
        )["QueueUrl"]

        # Assinaturas: cada fila "escuta" o tópico.
        # RawMessageDelivery=true → entrega o JSON puro, sem envelope SNS.
        for url_da_fila in [self.url_fila_estoque, self.url_fila_notificacao]:
            sns.subscribe(
                TopicArn=self.arn_do_topico,
                Protocol="sqs",
                Endpoint=_obter_arn_da_fila(sqs, url_da_fila),
                Attributes={"RawMessageDelivery": "true"},
            )

        # Drena mensagens de execuções anteriores para isolar este módulo de testes
        drain_queue(sqs, self.url_fila_estoque)
        drain_queue(sqs, self.url_fila_notificacao)

    # ── Operações de negócio ──────────────────────────────────────────────────

    def publicar_pedido(self, pedido_id: str) -> str:
        """Publica um PedidoCriado no tópico SNS. Retorna o MessageId."""
        resposta = self._sns.publish(
            TopicArn=self.arn_do_topico,
            Message=json.dumps({"pedidoId": pedido_id}),
        )
        return resposta["MessageId"]

    def receber_da_fila_estoque(self) -> list:
        """Recebe (sem deletar) até 10 mensagens da fila de estoque."""
        return self._sqs.receive_message(
            QueueUrl=self.url_fila_estoque,
            MaxNumberOfMessages=10,
            VisibilityTimeout=5,
        ).get("Messages", [])

    def receber_da_fila_notificacao(self) -> list:
        """Recebe (sem deletar) até 10 mensagens da fila de notificação."""
        return self._sqs.receive_message(
            QueueUrl=self.url_fila_notificacao,
            MaxNumberOfMessages=10,
            VisibilityTimeout=5,
        ).get("Messages", [])

    def pedido_chegou_na_fila_estoque(self, pedido_id: str) -> bool:
        return any(pedido_id in m["Body"] for m in self.receber_da_fila_estoque())

    def pedido_chegou_na_fila_notificacao(self, pedido_id: str) -> bool:
        return any(pedido_id in m["Body"] for m in self.receber_da_fila_notificacao())

    def pedido_chegou_nas_duas_filas(self, pedido_id: str) -> bool:
        """Verifica se o mesmo pedido chegou simultaneamente nas duas filas."""
        return (
            self.pedido_chegou_na_fila_estoque(pedido_id)
            and self.pedido_chegou_na_fila_notificacao(pedido_id)
        )


# ── U1V8 — Tabela de Deduplicação e Processador de Pedidos ───────────────────


class TabelaDeDeduplicacao:
    """
    Representa a tabela DynamoDB que registra os messageIds processados.

    TTL (Time to Live) ativado no campo 'expira_em': o DynamoDB apaga o
    registro automaticamente após 24h — sem limpeza manual, sem custo extra.

    Uso:
        tabela = TabelaDeDeduplicacao(dynamodb)
        assert tabela.pedido_foi_registrado("P-001")
    """

    NOME = "mensagens-processadas"

    def __init__(self, dynamodb):
        self._dynamodb = dynamodb
        self._criar_se_nao_existe()

    def _criar_se_nao_existe(self):
        try:
            self._dynamodb.create_table(
                TableName=self.NOME,
                AttributeDefinitions=[
                    {"AttributeName": "messageId", "AttributeType": "S"}
                ],
                KeySchema=[{"AttributeName": "messageId", "KeyType": "HASH"}],
                BillingMode="PAY_PER_REQUEST",
            )
            wait_until(
                lambda: self._dynamodb.describe_table(TableName=self.NOME)
                                     ["Table"]["TableStatus"] == "ACTIVE",
                timeout=30,
                message="tabela DynamoDB não ficou ACTIVE",
            )
        except self._dynamodb.exceptions.ResourceInUseException:
            pass  # tabela já existe — ok em execuções repetidas

        # TTL: campo epoch que o DynamoDB usa para apagar o registro após a data
        self._dynamodb.update_time_to_live(
            TableName=self.NOME,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "expira_em"},
        )

    # ── Consultas de negócio ──────────────────────────────────────────────────

    def pedido_foi_registrado(self, message_id: str) -> bool:
        """Verifica se o messageId foi gravado após o processamento."""
        resposta = self._dynamodb.get_item(
            TableName=self.NOME,
            Key={"messageId": {"S": message_id}},
        )
        return "Item" in resposta

    def obter_registro(self, message_id: str) -> dict | None:
        """Retorna o registro completo de controle ou None se não existir."""
        resposta = self._dynamodb.get_item(
            TableName=self.NOME,
            Key={"messageId": {"S": message_id}},
        )
        return resposta.get("Item")

    def contar_registros(self, message_id: str) -> int:
        """
        Conta registros para um messageId.
        Deve ser sempre 1 — mais de 1 significa que uma duplicata escapou.
        """
        resultado = self._dynamodb.query(
            TableName=self.NOME,
            KeyConditionExpression="messageId = :id",
            ExpressionAttributeValues={":id": {"S": message_id}},
        )
        return resultado["Count"]


class ProcessadorDePedidos:
    """
    Encapsula o deploy e a invocação da Lambda processa_pedido.

    Uso:
        processador = ProcessadorDePedidos(lam, tabela.NOME)
        resposta = processador.processar("P-001")
        assert not processador.retornou_erro(resposta)
    """

    NOME = "processa-pedido"
    HANDLER = "processa_pedido.lambda_handler"
    CAMINHO = "src/U1V8_idempotencia/processa_pedido.py"

    def __init__(self, lam, nome_da_tabela: str):
        self._lam = lam
        deploy_lambda(
            lambda_client=lam,
            function_name=self.NOME,
            source_path=self.CAMINHO,
            handler=self.HANDLER,
            env_vars={"DYNAMODB_TABLE": nome_da_tabela},
        )

    def processar(self, message_id: str) -> dict:
        """
        Invoca a Lambda com um evento SQS simulado.
        Formato imita o que o SQS enviaria via ESM:
        {"Records": [{"body": "{...}"}]}
        """
        evento_sqs = {
            "Records": [
                {"body": json.dumps({"messageId": message_id, "valor": "99.90"})}
            ]
        }
        return self._lam.invoke(
            FunctionName=self.NOME,
            InvocationType="RequestResponse",
            Payload=json.dumps(evento_sqs).encode(),
        )

    def retornou_erro(self, resposta: dict) -> bool:
        """
        FunctionError presente na resposta indica exceção não tratada.
        Para duplicatas, o handler deve retornar 200 sem FunctionError.
        """
        return "FunctionError" in resposta


# ── U1V9 — Fila com DLQ e Consumidora ────────────────────────────────────────


class FilaComDlq:
    """
    Cria uma fila SQS com Dead-Letter Queue (DLQ) vinculada.

    RedrivePolicy: configuração na fila PRINCIPAL que define para onde
    enviar mensagens rejeitadas repetidamente e quantas tentativas
    são permitidas antes do roteamento para a DLQ.

    maxReceiveCount: número de recepções com falha antes de rotear para a DLQ.
    VisibilityTimeout: intervalo em segundos entre as tentativas de retry.

    Uso:
        fila = FilaComDlq(sqs, "fila-pedidos", "fila-pedidos-dlq")
        fila.enviar_mensagem({"sku": "ABC", "defeituoso": True})
        assert fila.mensagem_chegou_na_fila_morta("ABC")
    """

    TEMPO_DE_VISIBILIDADE_EM_SEGUNDOS = 10  # Curto para agilizar testes

    def __init__(self, sqs, nome_da_fila: str, nome_da_dlq: str, max_tentativas: int = 3):
        self._sqs = sqs

        # Cria a DLQ primeiro — precisa do ARN antes de criar a fila principal
        self.url_fila_morta = sqs.create_queue(QueueName=nome_da_dlq)["QueueUrl"]
        arn_da_dlq = _obter_arn_da_fila(sqs, self.url_fila_morta)

        # RedrivePolicy: vincula a fila principal à DLQ
        politica_de_reenvio = json.dumps({
            "deadLetterTargetArn": arn_da_dlq,
            "maxReceiveCount": str(max_tentativas),
        })

        self.url_fila_principal = sqs.create_queue(
            QueueName=nome_da_fila,
            Attributes={
                "VisibilityTimeout": str(self.TEMPO_DE_VISIBILIDADE_EM_SEGUNDOS),
                "RedrivePolicy": politica_de_reenvio,
            },
        )["QueueUrl"]

    # ── Operações de negócio ──────────────────────────────────────────────────

    def enviar_mensagem(self, corpo: dict) -> None:
        """Envia uma mensagem para a fila principal."""
        self._sqs.send_message(
            QueueUrl=self.url_fila_principal,
            MessageBody=json.dumps(corpo),
        )

    def receber_da_fila_morta(self) -> list:
        """Recebe (sem deletar) até 10 mensagens da DLQ."""
        return self._sqs.receive_message(
            QueueUrl=self.url_fila_morta,
            MaxNumberOfMessages=10,
            VisibilityTimeout=5,
        ).get("Messages", [])

    def mensagem_chegou_na_fila_morta(self, identificador: str) -> bool:
        """Verifica se uma mensagem com o identificador chegou na DLQ."""
        return any(
            identificador in m["Body"]
            for m in self.receber_da_fila_morta()
        )


class ConsumidoraDeEstoque:
    """
    Encapsula o deploy da Lambda consumidora_b e a criação do ESM.

    Ao ser instanciada, faz o deploy e vincula a fila via ESM (Event Source
    Mapping): a partir desse momento, mensagens na fila disparam a Lambda
    automaticamente.

    Uso:
        consumidora = ConsumidoraDeEstoque(lam, fila.url_fila_principal)
        # a partir daqui, mensagens na fila disparam a Lambda
    """

    NOME = "consumidora-b"
    HANDLER = "consumidora_b.lambda_handler"
    CAMINHO = "src/U1V9_dlq/consumidora_b.py"

    def __init__(self, lam, url_da_fila_principal: str):
        deploy_lambda(
            lambda_client=lam,
            function_name=self.NOME,
            source_path=self.CAMINHO,
            handler=self.HANDLER,
        )
        # ESM: cria o vínculo SQS → Lambda
        arn_da_fila = _obter_arn_da_fila(
            _cliente_sqs_auxiliar(), url_da_fila_principal
        )
        _criar_esm(lam, self.NOME, arn_da_fila)


def _cliente_sqs_auxiliar():
    """
    Cria um cliente SQS temporário para uso interno dos builders.
    Lê AWS_ENDPOINT_URL automaticamente — sem hardcode de endpoint.
    """
    import boto3
    import os
    endpoint = os.environ.get("AWS_ENDPOINT_URL")
    kwargs = dict(region_name="us-east-1", endpoint_url=endpoint)
    if endpoint and "localhost" in endpoint:
        kwargs["aws_access_key_id"] = "test"
        kwargs["aws_secret_access_key"] = "test"
    return boto3.client("sqs", **kwargs)


# ── U2 — Event Sourcing ───────────────────────────────────────────────────────


class ContaBancariaEventStore:
    """
    Provisiona a tabela `eventos` (append-only, com DynamoDB Streams) para os
    testes de Event Sourcing. Expõe o nome da tabela; a lógica de negócio vive
    em src/U2_event_sourcing/.
    """

    NOME_TABELA = "eventos"

    def __init__(self, dynamodb):
        self._dynamodb = dynamodb
        self._criar_se_nao_existe()

    def _criar_se_nao_existe(self):
        existentes = self._dynamodb.meta.client.list_tables()["TableNames"]
        if self.NOME_TABELA in existentes:
            self.tabela = self._dynamodb.Table(self.NOME_TABELA)
            return
        self.tabela = self._dynamodb.create_table(
            TableName=self.NOME_TABELA,
            AttributeDefinitions=[
                {"AttributeName": "aggregate_id", "AttributeType": "S"},
                {"AttributeName": "sequencia", "AttributeType": "N"},
            ],
            KeySchema=[
                {"AttributeName": "aggregate_id", "KeyType": "HASH"},
                {"AttributeName": "sequencia", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
            StreamSpecification={"StreamEnabled": True, "StreamViewType": "NEW_IMAGE"},
        )
        self.tabela.wait_until_exists()

    def arn_do_stream(self) -> str:
        desc = self._dynamodb.meta.client.describe_table(TableName=self.NOME_TABELA)
        return desc["Table"]["LatestStreamArn"]


class TabelaSnapshots:
    """Provisiona a tabela `snapshots` (PK aggregate_id) para os testes de replay."""

    NOME_TABELA = "snapshots"

    def __init__(self, dynamodb):
        self._dynamodb = dynamodb
        existentes = dynamodb.meta.client.list_tables()["TableNames"]
        if self.NOME_TABELA in existentes:
            self.tabela = dynamodb.Table(self.NOME_TABELA)
            return
        self.tabela = dynamodb.create_table(
            TableName=self.NOME_TABELA,
            AttributeDefinitions=[{"AttributeName": "aggregate_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "aggregate_id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        self.tabela.wait_until_exists()


# ── U2 — Projeção CQRS via DynamoDB Streams ──────────────────────────────────


class ProjecaoSaldo:
    """
    Provisiona a tabela de leitura `saldo_atual` e a Lambda `projecao-saldo`,
    que é acionada automaticamente pelo DynamoDB Streams da tabela `eventos`.

    Uso:
        store = ContaBancariaEventStore(dynamodb_resource)
        projecao = ProjecaoSaldo(dynamodb_resource, lam)
        # a partir daqui, eventos gravados em `eventos` propagam para `saldo_atual`
    """

    NOME_TABELA = "saldo_atual"
    NOME_FUNCAO = "projecao-saldo"
    HANDLER = "projecao.lambda_handler"
    CAMINHO = "src/U2_event_sourcing/projecao.py"

    def __init__(self, dynamodb, lam):
        import os
        self._dynamodb = dynamodb
        self._lam = lam
        self._endpoint = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
        # Dentro do container Lambda, `localhost` aponta para o próprio container,
        # não para o LocalStack. Detectamos o IP real do container LocalStack via
        # Docker para que a Lambda consiga alcançar o DynamoDB.
        self._endpoint_interno = self._endpoint_localstack_interno()

        self._criar_tabela_saldo_se_nao_existe()
        self._deploy_lambda()
        self._criar_esm_stream()

    @staticmethod
    def _endpoint_localstack_interno() -> str:
        """
        Retorna o endpoint que a Lambda (container Docker) deve usar para alcançar
        o LocalStack. Se o LocalStack estiver rodando como container Docker no
        mesmo host, usa o IP do container. Caso contrário, retorna o endpoint padrão.
        """
        import subprocess, os
        endpoint_externo = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
        try:
            resultado = subprocess.run(
                ["docker", "inspect",
                 "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                 "serverless-event-driven-localstack-1"],
                capture_output=True, text=True, timeout=5
            )
            ip = resultado.stdout.strip().split("\n")[0]
            if ip:
                # Extrai a porta do endpoint externo
                from urllib.parse import urlparse
                porta = urlparse(endpoint_externo).port or 4566
                return f"http://{ip}:{porta}"
        except Exception:
            pass
        return endpoint_externo

    def _criar_tabela_saldo_se_nao_existe(self):
        existentes = self._dynamodb.meta.client.list_tables()["TableNames"]
        if self.NOME_TABELA in existentes:
            self.tabela = self._dynamodb.Table(self.NOME_TABELA)
            return
        self.tabela = self._dynamodb.create_table(
            TableName=self.NOME_TABELA,
            AttributeDefinitions=[{"AttributeName": "conta_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "conta_id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        self.tabela.wait_until_exists()

    def _deploy_lambda(self):
        env_vars = {
            "TABELA_SALDO": self.NOME_TABELA,
            "AWS_ENDPOINT_URL": self._endpoint_interno,
        }
        # Remove a função existente para garantir que o novo container suba com
        # o endpoint correto (LocalStack recicla containers; o antigo teria localhost).
        try:
            self._lam.delete_function(FunctionName=self.NOME_FUNCAO)
            import time
            time.sleep(2)  # aguarda exclusão propagar no LocalStack
        except self._lam.exceptions.ResourceNotFoundException:
            pass  # não existia — tudo bem

        deploy_lambda(
            lambda_client=self._lam,
            function_name=self.NOME_FUNCAO,
            source_path=self.CAMINHO,
            handler=self.HANDLER,
            env_vars=env_vars,
        )

    def _criar_esm_stream(self):
        """Cria o Event Source Mapping: DynamoDB Stream → Lambda `projecao-saldo`."""
        import time
        # A tabela `eventos` deve existir com Streams — ContaBancariaEventStore garante isso
        arn_stream = ContaBancariaEventStore(self._dynamodb).arn_do_stream()

        # Remove ESMs órfãos para a mesma source (podem ter ficado após delete_function)
        esms_existentes = self._lam.list_event_source_mappings(
            EventSourceArn=arn_stream
        ).get("EventSourceMappings", [])
        for esm in esms_existentes:
            try:
                self._lam.delete_event_source_mapping(UUID=esm["UUID"])
            except Exception:
                pass  # já removido ou sem permissão — segue em frente

        # Aguarda todos os ESMs anteriores serem removidos antes de criar o novo
        if esms_existentes:
            time.sleep(3)

        self._lam.create_event_source_mapping(
            EventSourceArn=arn_stream,
            FunctionName=self.NOME_FUNCAO,
            StartingPosition="LATEST",
            BatchSize=1,
            Enabled=True,
        )

        # Aguarda o poller do LocalStack se inicializar antes de retornar.
        # Sem esse delay, eventos escritos imediatamente após a criação do ESM
        # podem ser perdidos porque o poller ainda não está ativo.
        time.sleep(5)

    def saldo(self, conta_id: str):
        """Retorna o saldo projetado para a conta ou Decimal('0') se não existir."""
        from src.U2_event_sourcing.projecao import obter_saldo
        return obter_saldo(conta_id, dynamodb_resource=self._dynamodb)
