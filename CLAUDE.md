# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Video Insight is a university monorepo (Insper, "Projeto de Software") for asynchronous AI video processing: a user uploads an MP4 (MVP limit: 10 min, 100 MB) and receives a timestamped Portuguese transcription, a summary and automatic chapters. All documentation, READMEs, code comments and user-facing messages are written in **Portuguese (pt-BR)**; keep new docs and comments in Portuguese. Commits follow Conventional Commits in English (`feat(gateway): ...`, `fix(ci): ...`, `docs: ...`).

The Job Service and the Processing Service implement their parts (see each service README); the Video Service still only exposes `GET /health`. The RabbitMQ topology, MinIO buckets/keys and artifact formats shared by Job and Processing Service are documented in `contracts/README.md` and `contracts/artifacts/`. In particular, `processing-service.requests` must be declared with exactly `x-dead-letter-exchange=video-insight.processing.dlx` and no routing key, or RabbitMQ rejects whichever service declares it second. Product scope and requirements live in `docs/contexto-produto-videos-ia.md`; the architectural decision in `docs/decisoes/adr-001-processamento-videos-ia.md`.

## Architecture

- **API Gateway** (`apps/api-gateway`, KrakenD CE, config-only in `krakend.json`): single HTTP entry point. Routes `/videos` → Video Service, `/jobs` → Job Service. No business logic, no DB access, never receives video bytes (uploads go directly to object storage via signed URLs).
- **Video Service** (`services/video-service`, Java 21 / Spring Boot 4, Maven): video metadata, ownership, validation, signed URLs. Own PostgreSQL.
- **Job Service** (`services/job-service`, Java 21 / Spring Boot 4, Maven): processing jobs, state transitions, progress, retries, idempotency. Own PostgreSQL (Flyway migrations); never touches media. Key mechanics spread across packages:
  - `processing.requested` is written to `outbox_events` in the same transaction as the job and published by a scheduled `OutboxPublisher` — never publish to RabbitMQ directly from a request.
  - Incoming events go `ProcessingEventListener` → `EventParser` (validation; invalid → DLQ) → `ProcessingEventHandler`, which dedupes by `event_id` (`processed_events`) and ignores events whose `attempt` differs from the job's or whose job is terminal. That is also how cancel works.
  - Creating a job calls the Video Service synchronously (`VideoClient`) to check the video exists and `upload_status == ready`.
  - On `processing.completed` it reads the artifact JSON from MinIO (`ArtifactStorage`) and stores the result in `job_results`.
  - No authentication yet: Auth0/OAuth2 and per-user ownership are planned for delivery 3 (the course's stage plan is in `Trabalho - Projeto de Software.pdf`); Prometheus metrics for delivery 4.
  - Uses Jackson 3 (`tools.jackson.*`; annotations still `com.fasterxml.jackson.annotation`) with global snake_case.
- **Processing Service** (`services/processing-service`, Python 3.12 / FastAPI, hatchling): a worker, not a public API. Work arrives only via RabbitMQ; the HTTP app exists only for the health check. Internal modules under `src/processing_service/`: `media` (FFmpeg), `transcription` (STT, TXT/SRT), `content_intelligence` (summary, chapters), `messaging` (idempotent consumer, event publishing). It writes artifacts to MinIO and communicates state only through events — it must not write to the other services' databases.
- **Frontend** (`apps/frontend`): placeholder, TypeScript, framework not yet chosen. Talks only to the Gateway.

Key boundaries: each business service owns its database (no shared DB); long-running work is triggered by messaging, never by holding HTTP requests open; `contracts/` holds no shared libraries or business logic.

### Contracts (`contracts/`)

Single source of truth for inter-component interfaces. OpenAPI 3.1 (`openapi/*.yaml`, JWT-protected) and JSON Schema Draft 2020-12 events (`events/*.schema.json`). Conventions: UUID ids, RFC 3339 UTC timestamps, breaking changes require a new contract version. Every event schema must require the envelope fields `event_id`, `event_type`, `event_version`, `occurred_at`, `correlation_id`, `data` and set `event_type` as a `const`. `scripts/validate_json_schemas.py` enforces this and also enforces the **exact** set of event types (`processing.requested|started|progressed|completed|failed`) — adding a new event requires updating `EXPECTED_EVENT_TYPES` there.

## Commands

Java services have no Maven wrapper; use a local `mvn` or build via Docker (the Dockerfile runs `mvn verify`, so `docker build` also runs the tests):

```bash
# Java (from services/video-service or services/job-service)
mvn verify                                        # job-service: fails below 80% line coverage (JaCoCo)
mvn test -Dtest=HealthControllerTest
mvn test -Dtest='JobApiTest#cancelsUnfinishedJobsOnlyOnce'
docker build -t video-insight/video-service services/video-service

# Processing Service (from services/processing-service)
python -m pip install '.[test]'
pytest
pytest tests/test_health.py::test_health
uvicorn processing_service.app:app --port 8080   # needs src on PYTHONPATH or the package installed

# Gateway config check
docker build -t video-insight/api-gateway apps/api-gateway
docker run --rm video-insight/api-gateway check -c /etc/krakend/krakend.json
```

Repository-wide validations run by CI (`.github/workflows/validate-repository.yml`), from the repo root:

```bash
npx --yes markdownlint-cli2@0.23.2 "**/*.md" "#.git/**"
python scripts/validate_json_schemas.py          # requires jsonschema
npx --yes @redocly/cli@2.51.2 lint --config redocly.yaml
docker compose --env-file .env.example -f infrastructure/compose.yaml config --quiet
```

CI also checks local Markdown links offline (lychee — broken relative links in any `.md` fail the build) and scans for secrets (gitleaks). Service jobs run only when their paths change, per `.github/paths-filter.yaml`.

Local dependencies (PostgreSQL ×2 on 5433/5434, RabbitMQ 5672/15672, MinIO 9000/9001, Prometheus 9090, Grafana 3000):

```bash
cp .env.example .env
docker compose --env-file .env -f infrastructure/compose.yaml up -d
docker compose --env-file .env -f infrastructure/compose.yaml --profile app up -d --build   # + Job Service on :8082
```

Job Service tests extend `IntegrationTest` (full Spring context on H2 in PostgreSQL mode, with `RabbitTemplate`, `VideoClient` and `ArtifactStorage` mocked), so they need no Docker; name test classes `*Test` so Surefire picks them up.

## Deployment (AWS)

`.github/workflows/deploy-aws.yml` deploys on push to `main` (or manual dispatch) to six pre-provisioned EC2 instances, one component per machine (Gateway, Video, Job, Processing, core data services, observability). Images are built in CI, shipped via `docker save` + `scp`, and run as `video-insight-*` containers, each published on host port **8081** (port 80 is blocked by AWS networking). The Gateway's `krakend.json` hardcodes the services' private VPC IPs (`172.31.x.x:8081`); deploy-time health checks hit `/health` and the Gateway's `/health/{video,jobs,processing}`.

The group cannot modify the AWS Security Group, so services reach PostgreSQL/RabbitMQ/MinIO on the core machine through persistent SSH tunnels (systemd units in `infrastructure/aws/tunnels/`), exposed to containers on the Docker bridge `172.17.0.1` (e.g. `15433` video DB, `15434` job DB, `15672` RabbitMQ, `19000` MinIO). Application config on AWS must use these tunnel endpoints, not the core machine's IP. See `infrastructure/aws/README.md` and `infrastructure/aws/tunnels/README.md`.

Containers run with tight memory limits (`--memory 320m` for services, JVM uses `-XX:MaxRAMPercentage=60`), so keep dependencies lean.

## Style

`.editorconfig`: UTF-8, LF, 2-space indent (4 for Python). Markdownlint disables line length (MD013) and table style (MD060).
