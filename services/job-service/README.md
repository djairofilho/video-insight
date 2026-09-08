# Job Service

Gerencia as solicitações assíncronas de processamento.

## Responsabilidades

- Criação, consulta e transições de estado dos jobs.
- Progresso, tentativas, cancelamento e idempotência.
- Publicação de solicitações no RabbitMQ.
- Consumo de eventos de progresso, conclusão e falha.
- Registro e consulta dos resultados estruturados.

O serviço terá banco PostgreSQL próprio e não manipulará arquivos de mídia.
Linguagem e framework serão escolhidos pelo responsável antes da implementação.
