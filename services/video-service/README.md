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

Localmente, com JDK 21 instalado. O Maven Wrapper baixa o Maven 3.9.11 na
primeira execução; no Windows, use `mvnw.cmd`.

```bash
./mvnw verify                                  # compila, testa e empacota
./mvnw test -Dtest=HealthControllerTest        # uma classe de teste
./mvnw spring-boot:run                         # sobe em http://localhost:8080
```

Com Docker:

```bash
docker build -t video-insight/video-service .
docker run --rm -p 8080:8080 video-insight/video-service
```
