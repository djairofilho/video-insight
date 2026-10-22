# Infraestrutura

Configuração do ambiente local e dos componentes compartilhados do Video
Insight.

O Docker Compose fornece:

- PostgreSQL independente para Video Service e Job Service;
- RabbitMQ com interface de administração;
- MinIO com API e console;
- Prometheus;
- Grafana com o Prometheus provisionado como fonte de dados.

O deploy atual usa cinco instâncias EC2 e está documentado em
[`aws/README.md`](aws/README.md).

## Iniciar o ambiente

Na raiz do repositório:

```powershell
Copy-Item .env.example .env
docker compose --env-file .env -f infrastructure/compose.yaml up -d
docker compose --env-file .env -f infrastructure/compose.yaml ps
```

No Linux ou macOS, substitua `Copy-Item` por `cp`.

Para subir também o Job Service, compilado a partir do código local, adicione
o profile `app`:

```powershell
docker compose --env-file .env -f infrastructure/compose.yaml --profile app up -d --build
```

## Endereços locais

| Componente | Endereço padrão |
|---|---|
| PostgreSQL do Video Service | `localhost:5433` |
| PostgreSQL do Job Service | `localhost:5434` |
| RabbitMQ | `localhost:5672` |
| Administração do RabbitMQ | `http://localhost:15672` |
| API do MinIO | `http://localhost:9000` |
| Console do MinIO | `http://localhost:9001` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |
| Job Service (profile `app`) | `http://localhost:8082` |

Os usuários, senhas e portas podem ser alterados no arquivo `.env`. Os valores
do `.env.example` destinam-se exclusivamente ao desenvolvimento local.

## Encerrar o ambiente

```powershell
docker compose --env-file .env -f infrastructure/compose.yaml down
```

Adicionar `--volumes` remove permanentemente os dados locais e deve ser feito
somente quando essa exclusão for intencional.

## Imagem local do MinIO

O Compose constrói o MinIO a partir dos binários oficiais do release GitHub,
verificados por SHA-256, em `minio/Dockerfile`. O build suporta AMD64 e ARM64
(Apple Silicon), sem depender das imagens indisponíveis no Quay/Docker Hub.
A primeira execução precisa de acesso ao GitHub e ao registry da imagem Debian.
Nenhum login no Quay é necessário. Para reconstruir explicitamente:

```bash
docker compose --env-file .env -f infrastructure/compose.yaml build minio
```

## Serviços Java com configuração local

Na raiz, execute em terminais separados:

```bash
bash scripts/run-local-service.sh video
bash scripts/run-local-service.sh job
```

O script lê `.env` e `apps/frontend/.env.local`, configura as credenciais locais,
ativa Auth0 e usa a porta `MINIO_API_PORT` também no cliente Java e nas URLs
assinadas. O Maven Wrapper do Video Service executa os dois projetos.

Se PHP-FPM ou outro processo ocupar 9000 no host, altere `MINIO_API_PORT=19000`
no `.env` e recrie apenas MinIO, preservando os dados:

```bash
docker compose --env-file .env -f infrastructure/compose.yaml up -d --no-build minio
```

Reinicie os serviços Java com os scripts acima após alterar portas ou credenciais.
O console MinIO continua em 9001, a menos que `MINIO_CONSOLE_PORT` seja alterado.
