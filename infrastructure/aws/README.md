# Deploy na AWS

Os endereços reais são Secrets do GitHub. Os nomes `*.internal` abaixo são
rótulos ilustrativos, sem resolução DNS configurada. O renderer substitui os
parâmetros somente no runner; consulte o [guia de secrets](../../docs/autenticacao-e-deploy.md).

A primeira entrega usa instâncias EC2 já fornecidas para a disciplina. A
implantação inicial substitui os workloads anteriores autorizados pelo grupo e
usa contêineres identificados com o prefixo `video-insight`.

| Responsável pela máquina | Componente nesta entrega | Endereço privado |
|---|---|---|
| Djairo | Nginx de entrada e KrakenD API Gateway | `host-configurado.internal` |
| Matheus Pereira | Video Service | `video.private.internal` |
| Eduardo Marcelino | Processing Service | `processing.private.internal` |
| Ruan | PostgreSQL, RabbitMQ e MinIO | `core.private.internal` |
| Leonardo Moretti | Job Service, Prometheus e Grafana | `job.private.internal` |

Nginx publica a porta `8081`; KrakenD escuta em `127.0.0.1:8082`. Os três serviços são acessados pelo
Gateway através da rede privada da VPC. O Caddy publica HTTPS de objetos na
porta `8081` do Core e encaminha as operações ao MinIO privado. O console
permanece restrito a `127.0.0.1:9001`. O Security Group compartilhado
permite TCP `8081`, utilizado pelo storage HTTPS e pela entrada do Gateway;
a administração disponível por SSH não permite alterar o Security Group.
Nos serviços internos, a entrada `8081` deve ser restringida ao Gateway
(`host-configurado.internal`), exceto a consulta do Job Service ao Video Service.

## Conectividade de dados

Como o grupo não pode alterar o Security Group, PostgreSQL e RabbitMQ são
alcançados pelos serviços através de túneis SSH persistentes na porta `22`.
Video, Job e Processing Service também usam túneis para a API privada do MinIO
em `9000`. A chave restrita do Job Service recebe apenas esse encaminhamento
adicional; a porta pública `8081` agora termina HTTPS no Caddy.
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
- secrets `AWS_GATEWAY_HOST`, `AWS_VIDEO_HOST`, `AWS_PROCESSING_HOST`,
  `AWS_CORE_HOST` e `AWS_OBSERVABILITY_HOST`;
- secrets `VIDEO_DB_PASSWORD`, `JOB_DB_PASSWORD`, `RABBITMQ_PASSWORD`,
  `MINIO_ROOT_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`, `GROQ_API_KEY` e
  `GEMINI_API_KEY`.

O Job Service recebe suas variáveis por `/opt/video-insight/job/job.env`, gerado
pelo workflow a partir dos secrets. Ele chama o Video Service em
`video.private.internal:8081`, então a restrição da porta `8081` do Video Service deve
liberar também o Job Service (`job.private.internal`).

O workflow exige autenticação e endpoints públicos HTTPS. Veja o guia de
[Auth0, proxy HTTPS e frontend na Vercel](../../docs/autenticacao-e-deploy.md) para criar
o tenant, configurar as novas variables do GitHub e publicar o frontend.
`STORAGE_PUBLIC_ENDPOINT` é fornecido por secret do GitHub e usado pelos dois
serviços que emitem URLs assinadas. Os buckets permanecem privados.

Chaves privadas, senhas e arquivos `.env` não pertencem ao Git.

## Operação da entrega 4

Os serviços Java têm limite de memória de 512 MiB. O deploy mantém o contêiner
anterior como `video-insight-COMPONENTE-rollback-DATA` e restaura-o caso a nova
versão falhe. Não exclua backups antes de verificar o aceite da versão nova.

Prometheus coleta dez alvos: quatro componentes da aplicação, cinco máquinas e
o próprio Prometheus. Grafana provisiona os painéis `Video Insight: operação`
(UID `video-insight`) e `Video Insight: máquinas e alertas`
(UID `video-insight-infra`), preservando datasource e volumes existentes. A porta privada 9090 não deve ser aberta diretamente à internet.

Acesse <https://grafana.alyvera.pro> e <https://prometheus.alyvera.pro>, ambos
com autenticação administrativa. A Vercel encaminha HTTPS ao Core, que usa
SSH até os serviços privados. O acesso abaixo permanece como alternativa:

```bash
ssh -N -L 13000:127.0.0.1:3000 -L 19090:job.private.internal:9090 -i ../projsoft26b.pem ubuntu@observability.internal
```

Abra `http://localhost:13000` e use a conta Grafana existente. O túnel precisa
permanecer ativo. O endereço `http://localhost:19090/targets` mostra os scrapes.
O pipeline Vercel exige `VERCEL_TOKEN`, `VERCEL_ORG_ID` e `VERCEL_PROJECT_ID`.

Detalhes dos uploads diretos, orçamento gratuito, alertas e restrições de rede:
[guia de operação](../../docs/operacao-infra.md).
