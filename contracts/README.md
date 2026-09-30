# Contratos

Fonte única dos contratos públicos entre os componentes.

- `openapi`: APIs REST do Video Service e Job Service.
- `events`: eventos trocados pelo RabbitMQ.
- `artifacts`: arquivos JSON gravados pelo Processing Service no MinIO.

Mudanças incompatíveis exigem nova versão do contrato. Este diretório não deve
conter regras de negócio nem bibliotecas compartilhadas entre os serviços.

## Convenções

- APIs descritas com OpenAPI 3.1 e protegidas por JWT.
- Identificadores no formato UUID.
- Datas e horários no formato RFC 3339, sempre em UTC.
- Eventos com `event_id`, `event_type`, `event_version`, `occurred_at`,
  `correlation_id` e `data`.
- Schemas de eventos descritos com JSON Schema Draft 2020-12.

## APIs

- [`openapi/video-service.yaml`](openapi/video-service.yaml)
- [`openapi/job-service.yaml`](openapi/job-service.yaml)

## Eventos

- `processing.requested`: solicita o início de um processamento.
- `processing.started`: informa que um worker iniciou a execução.
- `processing.progressed`: atualiza etapa e percentual estimado.
- `processing.completed`: informa os artefatos produzidos.
- `processing.failed`: registra a causa e se a falha permite nova tentativa.

## Mensageria

Topologia combinada entre Job Service e Processing Service.

| Item | Valor |
|---|---|
| Exchange de eventos | `video-insight.processing` (tipo `topic`, durável) |
| Routing key | igual ao `event_type`, por exemplo `processing.requested` |
| Fila do Processing Service | `processing-service.requests`, ligada a `processing.requested` |
| DLX da fila do Processing Service | `video-insight.processing.dlx` (tipo `topic`) |
| DLQ do Processing Service | `processing-service.requests.dlq`, ligada à DLX com `#` |
| Fila do Job Service | `job-service.processing-events`, ligada aos demais eventos |
| DLX da fila do Job Service | `video-insight.dlx` (tipo `direct`) |
| DLQ do Job Service | `job-service.processing-events.dlq` |

- As mensagens são JSON persistentes (`content_type: application/json`) com
  `message_id` igual ao `event_id`.
- `processing-service.requests` é declarada com
  `x-dead-letter-exchange: video-insight.processing.dlx` e sem
  `x-dead-letter-routing-key`. Quem declarar essa fila deve usar exatamente
  esses argumentos, ou o RabbitMQ recusa a declaração.
- Cada serviço usa sua própria DLX, para que as mensagens rejeitadas de um não
  caiam na DLQ do outro.
- O `correlation_id` do `processing.requested` se repete em todos os eventos
  do job.
- Os consumidores devem ser idempotentes: a mesma mensagem pode chegar mais de
  uma vez, e uma tentativa já concluída pode ter `processing.completed`
  republicado.

## Armazenamento de objetos

- Vídeo original: bucket `videos`, na chave `{video_id}/original.mp4`. O Job
  Service envia essa chave em `storage_key`; o Video Service deve gravar o
  arquivo no mesmo lugar.
- Artefatos: bucket `artifacts`, com chaves `jobs/{job_id}/attempt-{n}/...`
  escolhidas pelo Processing Service e informadas em `processing.completed`.
- Os formatos dos artefatos JSON estão em [`artifacts`](artifacts/). O
  formato dos `blocks` dos capítulos está no
  [README do Processing Service](../services/processing-service/README.md).
