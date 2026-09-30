# Infraestrutura

Configuração do ambiente local e dos componentes compartilhados do Video
Insight.

O Docker Compose fornece:

- PostgreSQL independente para Video Service e Job Service;
- RabbitMQ com interface de administração;
- MinIO com API e console;
- Prometheus;
- Grafana com o Prometheus provisionado como fonte de dados.

O deploy da primeira entrega usa seis instâncias EC2 e está documentado em
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
