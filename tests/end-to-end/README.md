# Testes ponta a ponta

Exercitam Video Service, Job Service e Processing Service juntos, com
PostgreSQL, RabbitMQ e MinIO reais. Por padrão, as chamadas vão direto aos
serviços locais. Para a implantação atual, use `E2E_GATEWAY_URL` com a origem
Vercel e `E2E_HEALTH_BASE_URL` com a origem do Gateway. As chamadas de negócio
atravessam o proxy HTTPS e as URLs assinadas usam `/storage`.

| Arquivo | O que cobre |
|---|---|
| `test_video_and_job.py` | Upload direto ao MinIO, validações, consulta síncrona do Job ao Video, exclusão, falha e nova tentativa, cancelamento |
| `test_concurrency.py` | Uploads paralelos, confirmações e URLs simultâneas, mesma `Idempotency-Key` em paralelo, jobs concorrentes e exclusão durante a criação de jobs |
| `test_full_pipeline.py` | Transcrição, resumo, capítulos e exportação com Groq e Gemini reais, inclusive dois vídeos ao mesmo tempo |
| `test_authorization.py` | Token ausente/inválido e isolamento de duas contas em listas, IDs, URLs, exclusão, cancelamento e retry |

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
mvn spring-boot:run -Dspring-boot.run.arguments=--server.port=8081
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
| `E2E_ACCESS_TOKEN` | obrigatória | Access token válido da primeira conta; nunca passe no argumento do processo |
| `E2E_OTHER_ACCESS_TOKEN` | obrigatória no isolamento | Access token da segunda conta, com `sub` diferente |
| `E2E_GATEWAY_URL` | opcional | Origem comum para Video/Job, por exemplo `https://video-insight-ruby.vercel.app` |
| `E2E_HEALTH_BASE_URL` | origem do Gateway | Defina a origem real em configuração local privada; health não é uma rota da SPA |
| `E2E_STORAGE_PROXY_BASE` | `E2E_GATEWAY_URL/storage` | Proxy HTTPS de storage quando o backend emite URLs HTTP |
| `E2E_VIDEO_SERVICE_URL` | `http://localhost:8081` | Video Service |
| `E2E_JOB_SERVICE_URL` | `http://localhost:8082` | Job Service |
| `E2E_JOB_TIMEOUT_SECONDS` | `600` | Espera máxima por um job |

As variáveis podem vir do ambiente ou de linhas `E2E_*` no `.env` da raiz, que
não é versionado.

Os serviços precisam usar `AUTH_ENABLED=true`, o mesmo issuer e a audience
`https://video-insight-api`. Obtenha os tokens por Authorization Code com PKCE
usando contas suas. Senhas e Client Secret não pertencem aos testes.
Os testes criam recursos próprios; os casos de exclusão removem somente esses
recursos. Eles não limpam vídeos de terceiros. As URLs assinadas autorizam o
storage: o bearer da API nunca é encaminhado no PUT/GET do arquivo.

A expiração do JWT também é validada pelos testes Java `JwtValidationTest`.
Para teste real de expiração, reutilize um token de teste após seu `exp`, sem
alterar o JWT nem o relógio dos servidores.
