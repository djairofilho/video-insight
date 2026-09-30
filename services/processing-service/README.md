# Processing Service

Worker Python responsável pelo pipeline de mídia e IA. Consome
`processing.requested`, baixa o vídeo do MinIO, extrai o áudio com FFmpeg,
transcreve com Groq Whisper, gera resumo e capítulos com agentes Gemini, grava os
artefatos no MinIO e publica os eventos de progresso, conclusão ou falha.

O serviço não expõe API de negócio nem acessa PostgreSQL. O único endpoint HTTP é
`GET /health`, que também informa o estado do consumidor (`connected`,
`connecting` ou `disabled`).

## Módulos

- `messaging`: eventos do contrato, consumidor e publicador do RabbitMQ.
- `media`: `ffprobe` e extração do áudio em FLAC mono 16 kHz.
- `transcription`: transcrição com Groq e exportação TXT, SRT e JSON.
- `content_intelligence`: agentes de resumo e capítulos sobre o Gemini.
- `pipeline.py`: orquestra as etapas e traduz falhas em `processing.failed`.
- `worker.py`: monta o pipeline a partir da configuração.

## Mensageria

| Recurso | Nome | Observação |
|---|---|---|
| Exchange de eventos | `video-insight.processing` | `topic`, durável; routing key igual ao `event_type` |
| Fila de solicitações | `processing-service.requests` | durável, ligada a `processing.requested`, `prefetch=1` |
| Dead letter exchange | `video-insight.processing.dlx` | `topic`, durável |
| Dead letter queue | `processing-service.requests.dlq` | mensagens fora do contrato |

O Job Service publica `processing.requested` no exchange e consome os eventos
`processing.started`, `processing.progressed`, `processing.completed` e
`processing.failed` em uma fila própria. As mensagens são persistentes e usam
`message_id = event_id` e `correlation_id` do evento. O `correlation_id` da
solicitação é repetido em todos os eventos do job.

Falhas de processamento são publicadas como `processing.failed` com `retryable`
e a mensagem é confirmada. Uma nova tentativa é pedida pelo Job Service com
`attempt` incrementado.

## Artefatos

O vídeo é lido de `videos/<storage_key>`. Os artefatos ficam no bucket
`artifacts`, com chaves determinísticas por tentativa:

```text
jobs/<job_id>/attempt-<n>/transcript.json
jobs/<job_id>/attempt-<n>/transcript.txt
jobs/<job_id>/attempt-<n>/transcript.srt
jobs/<job_id>/attempt-<n>/summary.json
jobs/<job_id>/attempt-<n>/chapters.json
jobs/<job_id>/attempt-<n>/completed.json
```

`completed.json` é gravado por último. Se a mesma tentativa for reentregue, o
worker republica o resultado sem reprocessar. A transcrição é gravada antes do
resumo e dos capítulos, então uma falha nessas etapas não a perde.

- `transcript.json`: `language`, `duration_seconds` e `segments` com
  `start_seconds`, `end_seconds` e `text`.
- `summary.json`: `content_kind` e `text` em Markdown. O formato depende do tipo:
  tópicos para reuniões, tópicos com bullets para aulas e tutoriais.
- `chapters.json`: lista de capítulos contínuos com `title`, `start_seconds`,
  `end_seconds` e `blocks`. Os blocos são `paragraph`, `callout` (`definition`,
  `important`, `curiosity`, `warning`, `reflection`) e os diagramas `flow`,
  `cycle`, `comparison` e `tree`.

## IA

- Transcrição: Groq `whisper-large-v3-turbo`, com `verbose_json` e timestamps por
  segmento. Erros 429, 5xx e de rede são retentados com limite.
- Resumo: agente que classifica o conteúdo, recebe o guia de formato do tipo e
  entrega o Markdown validado.
- Capítulos: agente que publica o sumário com os tempos, emite cada capítulo e
  encerra. Cada bloco é validado e os erros voltam ao modelo para correção.
- Modelo: `gemini-3.5-flash-lite`. Os agentes têm limites de turnos, chamadas de
  ferramenta, tempo total e cutucadas.

## Configuração

| Variável | Padrão | Uso |
|---|---|---|
| `RABBITMQ_HOST` / `RABBITMQ_PORT` | `localhost` / `5672` | Na AWS, `172.17.0.1` / `15672` pelo túnel |
| `RABBITMQ_USER` / `RABBITMQ_PASSWORD` | `video_insight` / vazio | Senha obrigatória |
| `MINIO_ENDPOINT` | `localhost:9000` | Na AWS, `172.17.0.1:19000` pelo túnel |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | `video_insight` / vazio | Chave secreta obrigatória |
| `VIDEOS_BUCKET` / `ARTIFACTS_BUCKET` | `videos` / `artifacts` | Buckets de entrada e saída |
| `GROQ_API_KEY` | vazio | Obrigatória |
| `GROQ_MODEL` | `whisper-large-v3-turbo` | Modelo de transcrição |
| `GEMINI_API_KEY` | vazio | Obrigatória |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Modelo dos agentes |
| `GEMINI_FALLBACK_MODEL` | `gemini-3.1-flash-lite` | Alternado com o principal em 429/5xx; vazio desliga |
| `GEMINI_THINKING_LEVEL` | `medium` | `minimal`, `low`, `medium` ou `high` |
| `CONSUMER_ENABLED` | `true` | Desliga o consumidor mantendo o `/health` |

Sem uma credencial obrigatória o consumidor fica desativado e o erro aparece no
log; o `/health` continua respondendo. Os limites dos agentes também podem ser
ajustados por variáveis, como `CHAPTER_AGENT_MAX_TURNS`.

## Executar

```bash
docker build -t video-insight/processing-service .
docker run --rm -p 8080:8080 --env-file .env video-insight/processing-service
```

## Testes

```bash
python -m pip install '.[test]'
pytest
```

A suíte exige 80% de cobertura. Os testes marcados como `integration` usam
RabbitMQ e MinIO reais via Docker e FFmpeg instalado; sem eles, são ignorados.
