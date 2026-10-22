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

O Gateway publica as APIs na porta `8081`. Os três serviços são acessados pelo
Gateway através da rede privada da VPC. O MinIO publica somente sua API S3 na
porta `8081` da máquina de Ruan para upload e download por URLs assinadas; o
console permanece restrito a `127.0.0.1:9001`. O Security Group compartilhado
permite TCP `8081`, usado porque a porta `80` está bloqueada na camada de rede
da AWS. Nos serviços internos, a entrada `8081` deve ser restringida ao Gateway
(`172.31.7.117`), exceto a consulta do Job Service ao Video Service.

## Conectividade de dados

Como o grupo não pode alterar o Security Group, PostgreSQL e RabbitMQ são
alcançados pelos serviços através de túneis SSH persistentes na porta `22`.
Video Service e Processing Service também usam túneis para o MinIO. O Job
Service lê os artefatos pelo endereço privado `172.31.8.165:8081`, já liberado
para as URLs assinadas, pois sua chave SSH não permite encaminhar a porta `9000`.
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
  `MINIO_ROOT_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`, `GROQ_API_KEY` e
  `GEMINI_API_KEY`.

O Job Service recebe suas variáveis por `/opt/video-insight/job/job.env`, gerado
pelo workflow a partir dos secrets. Ele chama o Video Service em
`172.31.1.54:8081`, então a restrição da porta `8081` do Video Service deve
liberar também o Job Service (`172.31.7.191`).

O workflow exige autenticação e endpoints públicos HTTPS. Veja o guia de
[Auth0, HTTPS e frontend na EC2](../../docs/autenticacao-e-deploy.md) para criar
o tenant, configurar as novas variables do GitHub e publicar o frontend.
`STORAGE_PUBLIC_ENDPOINT` é fornecido por variable do GitHub e usado pelos dois
serviços que emitem URLs assinadas. Os buckets permanecem privados.

Chaves privadas, senhas e arquivos `.env` não pertencem ao Git.
