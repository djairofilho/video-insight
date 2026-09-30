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

> **Proposta provisória**, implementada pelo Job Service e ainda a validar com
> o Processing Service. Os nomes são configuráveis no Job Service.

| Item | Valor |
|---|---|
| Exchange de eventos | `video-insight.events` (tipo `topic`, durável) |
| Routing key | igual ao `event_type`, por exemplo `processing.requested` |
| Fila do Processing Service | `processing-service.requests`, ligada a `processing.requested` |
| Fila do Job Service | `job-service.processing-events`, ligada aos demais eventos |
| Exchange de mensagens rejeitadas | `video-insight.dlx` (tipo `direct`) |
| Filas de mensagens rejeitadas | nome da fila seguido de `.dlq` |

- As mensagens são JSON persistentes (`content_type: application/json`) com
  `message_id` igual ao `event_id`.
- As duas filas usam `x-dead-letter-exchange: video-insight.dlx` e
  `x-dead-letter-routing-key` igual ao nome da DLQ. Quem declarar uma fila deve
  usar exatamente esses argumentos, ou o RabbitMQ recusa a declaração.
- O Job Service declara toda a topologia, inclusive a fila de solicitações,
  para que nenhuma solicitação se perca antes de o worker se conectar.
- Os consumidores devem ser idempotentes: a mesma mensagem pode chegar mais de
  uma vez.

## Armazenamento de objetos

> **Proposta provisória**, a validar com Video Service e Processing Service.

- Bucket: `video-insight`.
- Vídeo original: `videos/{video_id}/original.mp4`. O Job Service envia esse
  valor em `storage_key`.
- As chaves dos artefatos são escolhidas pelo Processing Service e informadas
  em `processing.completed`.
- Os formatos dos artefatos JSON estão em [`artifacts`](artifacts/).
