# Túneis SSH

As portas de dados entre as instâncias são bloqueadas pela rede AWS e o grupo
não possui permissão para alterar o Security Group. Estas unidades systemd usam
a porta SSH `22` para disponibilizar as dependências somente na ponte local do
Docker (`172.17.0.1`).

| Máquina | Endpoint local para contêineres | Destino em Ruan |
|---|---|---|
| Matheus Pereira | `172.17.0.1:15433` | Video PostgreSQL `5433` |
| Matheus Pereira | `172.17.0.1:19000` | MinIO `9000` |
| Marcus | `172.17.0.1:15434` | Job PostgreSQL `5434` |
| Marcus | `172.17.0.1:15672` | RabbitMQ `5672` |
| Eduardo Marcelino | `172.17.0.1:15672` | RabbitMQ `5672` |
| Eduardo Marcelino | `172.17.0.1:19000` | MinIO `9000` |

Cada origem usa uma chave Ed25519 própria em
`/etc/video-insight/tunnel_ed25519`. As chaves autorizadas em Ruan limitam o
encaminhamento aos destinos da tabela e não são armazenadas no Git.

Os serviços de aplicação devem usar os endpoints locais da tabela. Nenhuma
porta de banco de dados, mensageria ou storage é aberta para a internet.
