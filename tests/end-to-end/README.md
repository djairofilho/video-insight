# Testes ponta a ponta

Exercitam Video Service, Job Service e Processing Service juntos, com
PostgreSQL, RabbitMQ e MinIO reais. Por padrão, as chamadas vão direto aos
serviços locais. Na AWS, defina `E2E_VIDEO_SERVICE_URL` e
`E2E_JOB_SERVICE_URL` com a mesma URL pública do Gateway; as URLs assinadas
usam a API S3 pública do MinIO.

| Arquivo | O que cobre |
|---|---|
| `test_video_and_job.py` | Upload direto ao MinIO, validações, consulta síncrona do Job ao Video, exclusão, falha e nova tentativa, cancelamento |
| `test_concurrency.py` | Uploads paralelos, confirmações e URLs simultâneas, mesma `Idempotency-Key` em paralelo, jobs concorrentes e exclusão durante a criação de jobs |
| `test_full_pipeline.py` | Transcrição, resumo, capítulos e exportação com Groq e Gemini reais, inclusive dois vídeos ao mesmo tempo |

Os dois primeiros usam um arquivo falso e não consomem cota: o worker o
rejeita antes de chamar a IA.

## Preparar o ambiente

Na raiz do repositório, com as dependências e o Job Service pelo Compose:

```bash
docker compose --env-file .env.example -f infrastructure/compose.yaml --profile app up -d --build --wait
```

Video Service na porta `8081`, onde o Job Service o procura:

```bash
cd services/video-service
./mvnw spring-boot:run -Dspring-boot.run.arguments=--server.port=8081
```

Processing Service na rede do Compose, com as chaves do Groq e do Gemini
exportadas no terminal:

```bash
docker build -t video-insight/processing-service services/processing-service
docker run -d --name vi-processing --network video-insight \
  -e GROQ_API_KEY -e GEMINI_API_KEY \
  -e RABBITMQ_HOST=rabbitmq -e RABBITMQ_PASSWORD=local-rabbitmq-password \
  -e MINIO_ENDPOINT=minio:9000 -e MINIO_SECRET_KEY=local-minio-password \
  video-insight/processing-service
```

## Executar

```bash
cd tests/end-to-end
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # no Linux/macOS: .venv/bin/python
.venv/Scripts/python -m pytest -v
.venv/Scripts/python -m pytest -v test_concurrency.py
```

| Variável | Padrão | Uso |
|---|---|---|
| `E2E_SAMPLE_VIDEO` | obrigatória no fluxo completo | MP4 curto com fala em português, até 10 min e 100 MB |
| `E2E_VIDEO_SERVICE_URL` | `http://localhost:8081` | Video Service |
| `E2E_JOB_SERVICE_URL` | `http://localhost:8082` | Job Service |
| `E2E_JOB_TIMEOUT_SECONDS` | `600` | Espera máxima por um job |

As variáveis podem vir do ambiente ou de linhas `E2E_*` no `.env` da raiz, que
não é versionado.
