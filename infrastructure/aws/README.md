# Deploy na AWS

A primeira entrega usa instâncias EC2 já fornecidas para a disciplina. A
implantação inicial substitui os workloads anteriores autorizados pelo grupo e
usa contêineres identificados com o prefixo `video-insight`.

| Responsável pela máquina | Componente nesta entrega | Endereço privado |
|---|---|---|
| Djairo | KrakenD API Gateway | `172.31.7.117` |
| Matheus Pereira | Video Service | `172.31.1.54` |
| Eduardo Marcelino | Processing Service | `172.31.14.236` |
| Ruan | PostgreSQL, RabbitMQ e MinIO | `172.31.8.165` |
| Leonardo Moretti | Job Service, Prometheus e Grafana | `172.31.7.191` |

O Gateway é a única entrada HTTP do produto e publica a porta `8081`. Os três
serviços são acessados pelo Gateway através da rede privada da VPC. O Security
Group compartilhado permite TCP `8081`, usado como alternativa porque a porta
`80` está bloqueada na camada de rede da AWS. Nos três serviços internos, a
entrada `8081` deve ser restringida ao Gateway (`172.31.7.117`).

## Conectividade de dados

Como o grupo não pode alterar o Security Group, PostgreSQL, RabbitMQ e MinIO
são alcançados pelos serviços através de túneis SSH persistentes na porta `22`.
As unidades systemd e os endpoints usados pelos contêineres estão documentados
em [`tunnels/README.md`](tunnels/README.md).

Cada túnel reinicia automaticamente e usa uma chave exclusiva, armazenada
somente na máquina de origem. Em Ruan, essas chaves permitem encaminhamento
apenas para as portas necessárias.

## Deploy automático

O workflow `deploy-aws.yml` é executado após mudanças na branch `main` e aplica
filtros por diretório. Cada serviço é compilado, testado, copiado por SSH e
substituído como contêiner Docker somente quando seus arquivos mudam. O Gateway
também é entregue como contêiner KrakenD.

O mesmo workflow instala e reinicia as unidades de túnel dos três serviços. A
criação inicial das chaves permanece uma operação de bootstrap das máquinas.
O MinIO é empacotado no CI com o binário da
[versão oficial](https://github.com/minio/minio/releases/tag/RELEASE.2025-09-07T16-13-09Z),
verificado por SHA-256, e carregado em Ruan antes do Docker Compose.
O workflow ajusta a propriedade do volume do MinIO para o usuário do contêiner
e espera os quatro componentes centrais ficarem saudáveis antes de concluir.

Na máquina de Leonardo, o Job Service usa a porta `8081`, enquanto Prometheus e
Grafana continuam nas portas `9090` e `3000`. Antes do primeiro deploy do Job
Service, configure nela a chave e o `known_hosts` do túnel para Ruan, conforme
[`tunnels/README.md`](tunnels/README.md).

O repositório precisa destas configurações no GitHub:

- secret `AWS_SSH_PRIVATE_KEY`;
- secret `AWS_KNOWN_HOSTS`;
- variables `AWS_GATEWAY_HOST`, `AWS_VIDEO_HOST`, `AWS_PROCESSING_HOST`,
  `AWS_CORE_HOST` e `AWS_OBSERVABILITY_HOST`;
- secrets `VIDEO_DB_PASSWORD`, `JOB_DB_PASSWORD`, `RABBITMQ_PASSWORD`,
  `MINIO_ROOT_PASSWORD` e `GRAFANA_ADMIN_PASSWORD`.

Chaves privadas, senhas e arquivos `.env` não pertencem ao Git.
