# Deploy na AWS

A primeira entrega usa instâncias EC2 já fornecidas para a disciplina. Os
workloads existentes são preservados; o Video Insight usa nomes próprios e a
porta `8081` nos serviços internos.

| Responsável pela máquina | Componente nesta entrega | Endereço privado |
|---|---|---|
| Djairo | KrakenD API Gateway | `172.31.7.117` |
| Matheus Pereira | Video Service | `172.31.1.54` |
| Marcus | Job Service | `172.31.13.221` |
| Eduardo Marcelino | Processing Service | `172.31.14.236` |
| Ruan | PostgreSQL, RabbitMQ e MinIO | `172.31.8.165` |
| Leonardo Moretti | Prometheus e Grafana | `172.31.7.191` |

O Gateway é a única entrada HTTP do produto e publica a porta `80`. Os três
serviços são acessados pelo Gateway através da rede privada da VPC.

## Deploy automático

O workflow `deploy-aws.yml` é executado após mudanças na branch `main` e aplica
filtros por diretório. Cada serviço é compilado, testado, copiado por SSH e
reiniciado com systemd somente quando seus arquivos mudam. O Gateway é entregue
como contêiner KrakenD.

O repositório precisa destas configurações no GitHub:

- secret `AWS_SSH_PRIVATE_KEY`;
- secret `AWS_KNOWN_HOSTS`;
- variables `AWS_GATEWAY_HOST`, `AWS_VIDEO_HOST`, `AWS_JOB_HOST` e
  `AWS_PROCESSING_HOST`, `AWS_CORE_HOST` e `AWS_OBSERVABILITY_HOST`;
- secrets `VIDEO_DB_PASSWORD`, `JOB_DB_PASSWORD`, `RABBITMQ_PASSWORD`,
  `MINIO_ROOT_PASSWORD` e `GRAFANA_ADMIN_PASSWORD`.

Chaves privadas, senhas e arquivos `.env` não pertencem ao Git.
