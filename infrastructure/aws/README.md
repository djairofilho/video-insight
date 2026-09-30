# Deploy na AWS

A primeira entrega usa instâncias EC2 já fornecidas para a disciplina. A
implantação inicial substitui os workloads anteriores autorizados pelo grupo e
usa contêineres identificados com o prefixo `video-insight`.

| Responsável pela máquina | Componente nesta entrega | Endereço privado |
|---|---|---|
| Djairo | KrakenD API Gateway | `172.31.7.117` |
| Matheus Pereira | Video Service | `172.31.1.54` |
| Marcus | Job Service | `172.31.13.221` |
| Eduardo Marcelino | Processing Service | `172.31.14.236` |
| Ruan | PostgreSQL, RabbitMQ e MinIO | `172.31.8.165` |
| Leonardo Moretti | Prometheus e Grafana | `172.31.7.191` |

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

O repositório precisa destas configurações no GitHub:

- secret `AWS_SSH_PRIVATE_KEY`;
- secret `AWS_KNOWN_HOSTS`;
- variables `AWS_GATEWAY_HOST`, `AWS_VIDEO_HOST`, `AWS_JOB_HOST` e
  `AWS_PROCESSING_HOST`, `AWS_CORE_HOST` e `AWS_OBSERVABILITY_HOST`;
- secrets `VIDEO_DB_PASSWORD`, `JOB_DB_PASSWORD`, `RABBITMQ_PASSWORD`,
  `MINIO_ROOT_PASSWORD` e `GRAFANA_ADMIN_PASSWORD`.

O Job Service recebe suas variáveis por `/opt/video-insight/job/job.env`, gerado
pelo workflow a partir dos secrets. Ele chama o Video Service em
`172.31.1.54:8081`, então a restrição da porta `8081` do Video Service deve
liberar também o Job Service (`172.31.13.221`).

As URLs de download geradas pelo Job Service apontam para o MinIO, que não é
público na AWS. Elas só funcionam fora da VPC quando houver um endereço público
para o MinIO, configurado em `STORAGE_PUBLIC_ENDPOINT`.

Chaves privadas, senhas e arquivos `.env` não pertencem ao Git.
