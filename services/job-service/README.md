# Job Service

Gerencia as solicitações assíncronas de processamento.

## Responsabilidades

- Criação, consulta e transições de estado dos jobs.
- Progresso, tentativas, cancelamento e idempotência.
- Publicação de solicitações no RabbitMQ.
- Consumo de eventos de progresso, conclusão e falha.
- Registro e consulta dos resultados estruturados.

O serviço usa Java 21 com Spring Boot, terá banco PostgreSQL próprio e não
manipulará arquivos de mídia. Nesta primeira entrega, o executável expõe
`GET /health`; as operações do contrato serão implementadas depois.

## Executar

```bash
docker build -t video-insight/job-service .
docker run --rm -p 8080:8080 video-insight/job-service
```
