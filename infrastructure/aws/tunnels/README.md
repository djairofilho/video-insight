# Túneis SSH

Os nomes de hosts deste documento são ilustrativos. A geração das unidades
substitui os parâmetros pelos secrets `AWS_DOCKER_BRIDGE_HOST` e
`AWS_CORE_PRIVATE_HOST`; os arquivos gerados não são versionados.

As portas de dados entre as instâncias são bloqueadas pela rede AWS e o grupo
não possui permissão para alterar o Security Group. Estas unidades systemd usam
a porta SSH `22` para disponibilizar as dependências somente na ponte local do
Docker (`docker.host.internal`).

| Máquina | Endpoint local para contêineres | Destino em Ruan |
|---|---|---|
| Matheus Pereira | `docker.host.internal:15433` | Video PostgreSQL `5433` |
| Matheus Pereira | `docker.host.internal:19000` | MinIO `9000` |
| Leonardo Moretti | `docker.host.internal:15434` | Job PostgreSQL `5434` |
| Leonardo Moretti | `docker.host.internal:15672` | RabbitMQ `5672` |
| Leonardo Moretti | `docker.host.internal:19000` | MinIO `9000` |
| Eduardo Marcelino | `docker.host.internal:15672` | RabbitMQ `5672` |
| Eduardo Marcelino | `docker.host.internal:19000` | MinIO `9000` |

Cada origem usa uma chave Ed25519 própria em
`/etc/video-insight/tunnel_ed25519`. As chaves autorizadas em Ruan limitam o
encaminhamento aos destinos da tabela e não são armazenadas no Git.

O Job Service também lê os artefatos pelo túnel local `19000`. O instalador
`allow-job-storage.py` acrescenta somente o destino MinIO à chave restrita que
já existia. Nenhuma chave privada é copiada entre servidores.

Video Service e Processing Service usam os endpoints locais da tabela. Os
buckets do MinIO permanecem privados; a porta `8081` do Core termina HTTPS com Caddy e aceita as URLs
assinadas de upload e download. O MinIO atende internamente em `9000`.

A coleta das máquinas também usa SSH, porque a rede AWS bloqueia as portas
`9100` e `9091` entre as instâncias. O monitor mantém uma chave própria, sem
acesso a shell, limitada a `9100` e, no gateway, a `9091`. As host keys são
obtidas por conexões administrativas já verificadas, sem aceitar hosts desconhecidos.
Veja [operação e limites](../../../docs/operacao-infra.md).
