# Contratos

Fonte única dos contratos públicos entre os componentes.

- `openapi`: APIs REST do Video Service e Job Service.
- `events`: eventos trocados pelo RabbitMQ.

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
