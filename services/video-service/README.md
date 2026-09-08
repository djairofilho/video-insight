# Video Service

Gerencia os vídeos como recursos do produto.

## Responsabilidades

- Metadados, propriedade e estados de upload.
- Validação de formato, tamanho e duração.
- URLs assinadas de upload, reprodução e download.
- Listagem, consulta e exclusão de vídeos.
- Integração com o armazenamento de objetos.

O serviço usa Java 21 com Spring Boot e terá banco PostgreSQL próprio. Nesta
primeira entrega, o executável expõe `GET /health`; as operações descritas no
contrato OpenAPI serão implementadas nas próximas entregas.

## Executar

```bash
docker build -t video-insight/video-service .
docker run --rm -p 8080:8080 video-insight/video-service
```
