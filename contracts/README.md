# Contratos

Fonte única dos contratos públicos entre os componentes.

- `openapi`: APIs REST do Video Service e Job Service.
- `events`: eventos trocados pelo RabbitMQ.

Mudanças incompatíveis exigem nova versão do contrato. Este diretório não deve
conter regras de negócio nem bibliotecas compartilhadas entre os serviços.
