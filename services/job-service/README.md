# Job Service

Gerencia as solicitações assíncronas de processamento.

## Responsabilidades

- Criação, consulta e transições de estado dos jobs.
- Progresso, tentativas, cancelamento e idempotência.
- Publicação de solicitações no RabbitMQ.
- Consumo de eventos de progresso, conclusão e falha.
- Registro e consulta dos resultados estruturados.

O serviço usa Java 21 com Spring Boot, tem banco PostgreSQL próprio e não
manipula arquivos de mídia. Ele implementa
[`job-service.yaml`](../../contracts/openapi/job-service.yaml) sob o prefixo
`/api/v1` e os eventos de [`contracts/events`](../../contracts/events/).

## Funcionamento

1. `POST /api/v1/videos/{videoId}/jobs` consulta o Video Service (comunicação
   síncrona) e só cria o job se o vídeo existir e estiver com `upload_status`
   igual a `ready`.
2. O job e o evento `processing.requested` são gravados na mesma transação. O
   evento fica na tabela `outbox_events` e é publicado no RabbitMQ a cada
   segundo, o que evita perder a solicitação se o broker estiver fora do ar.
3. Os eventos do Processing Service chegam pela fila
   `job-service.processing-events`. Cada `event_id` é aplicado uma única vez, e
   eventos de tentativas antigas ou de jobs finalizados são ignorados.
   Mensagens inválidas vão para a DLQ.
4. Em `processing.completed`, o serviço lê do MinIO os artefatos JSON indicados
   no evento e guarda o resultado estruturado em `job_results`.
5. `retry` cria uma nova tentativa e preserva a anterior em `job_attempts`.
   `cancel` finaliza o job, e eventos posteriores do worker são descartados.

A repetição do header `Idempotency-Key` com o mesmo pedido devolve o job já
criado; com um pedido diferente, a resposta é `409`.

A autenticação com Auth0 e a restrição de cada job ao seu dono entram na
etapa 3; nesta etapa os endpoints não exigem token.

## Configuração

| Variável | Padrão local |
|---|---|
| `DB_URL`, `DB_USER`, `DB_PASSWORD` | PostgreSQL do Job Service em `localhost:5434` |
| `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD` | `localhost:5672` |
| `STORAGE_ENDPOINT` | `http://localhost:9000` |
| `STORAGE_PUBLIC_ENDPOINT` | `http://localhost:9000`, usado nas URLs assinadas |
| `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_BUCKET` | credenciais locais do MinIO, bucket `artifacts` |
| `VIDEO_SERVICE_URL` | `http://localhost:8081` |
| `VIDEO_STORAGE_KEY_TEMPLATE` | `{videoId}/original.mp4`, chave no bucket `videos` |
| `MESSAGING_EXCHANGE`, `MESSAGING_EVENTS_QUEUE`, `MESSAGING_REQUESTS_QUEUE`, `MESSAGING_DLX`, `MESSAGING_REQUESTS_DLX` | nomes de [`contracts/README.md`](../../contracts/README.md) |

O estado das dependências fica em `/actuator/health`. O `GET /health` continua
disponível para o deploy.

## Testar

```bash
mvn verify
mvn test -Dtest=JobApiTest
mvn test -Dtest='JobApiTest#cancelsUnfinishedJobsOnlyOnce'
```

Os testes usam H2 em modo PostgreSQL e simulam RabbitMQ, MinIO e Video Service,
então não precisam de Docker. O `mvn verify` falha se a cobertura de linhas
ficar abaixo de 80%; o relatório fica em `target/site/jacoco/index.html`.

## Executar

Com as dependências de [`infrastructure`](../../infrastructure/README.md), a
partir da raiz do repositório:

```bash
docker compose --env-file .env -f infrastructure/compose.yaml --profile app up -d --build
```

O serviço fica em `http://localhost:8082`. Para rodar somente a imagem:

```bash
docker build -t video-insight/job-service .
docker run --rm -p 8080:8080 video-insight/job-service
```
