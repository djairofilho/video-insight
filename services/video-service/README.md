# Video Service

Gerencia os vídeos como recursos do produto.

## Responsabilidades

- Metadados e estados de upload.
- Validação de formato, tamanho e duração.
- URLs assinadas de upload e reprodução.
- Listagem, consulta e exclusão de vídeos.
- Integração com o armazenamento de objetos.

O serviço usa Java 21 com Spring Boot, tem banco PostgreSQL próprio e nunca
recebe o conteúdo dos vídeos: o navegador envia e baixa o arquivo direto do
MinIO por URLs assinadas. Ele implementa
[`video-service.yaml`](../../contracts/openapi/video-service.yaml) sob o prefixo
`/api/v1`.

## Funcionamento

1. `POST /api/v1/videos` cadastra o vídeo como `pending`. Só aceita
   `video/mp4` de até 100 MB.
2. `POST /api/v1/videos/{videoId}/upload-url` devolve uma URL `PUT` válida por
   15 minutos e o vídeo passa a `uploading`. O navegador deve enviar os
   `headers` devolvidos, porque o `Content-Type` faz parte da assinatura.
3. `POST /api/v1/videos/{videoId}/upload-complete` confere o arquivo no MinIO.
   - Sem arquivo, responde `409`.
   - Com tamanho diferente do cadastrado, o vídeo vira `failed` e responde `409`.
   - Caso contrário, grava a duração (até 600 s) e o vídeo vira `ready`.
     Repetir a confirmação devolve o mesmo vídeo.
4. `POST /api/v1/videos/{videoId}/playback-url` devolve uma URL `GET` para
   vídeos `ready`.
5. `DELETE /api/v1/videos/{videoId}` apaga o arquivo e depois o registro.

O arquivo fica no bucket `videos`, na chave `{video_id}/original.mp4`, como
combinado em [`contracts/README.md`](../../contracts/README.md). O bucket é
criado na inicialização se ainda não existir.

O Job Service consulta `GET /api/v1/videos/{videoId}` antes de criar um job
(comunicação síncrona) e só aceita vídeos `ready`. Alterações simultâneas no
mesmo vídeo usam versionamento otimista e não sobrescrevem umas às outras.

A listagem usa cursor opaco (`next_cursor`), com os vídeos mais recentes
primeiro. A autenticação com Auth0 e a restrição de cada vídeo ao seu dono
entram na etapa 3; nesta etapa os endpoints não exigem token.

## Configuração

| Variável | Padrão local |
|---|---|
| `DB_URL`, `DB_USER`, `DB_PASSWORD` | PostgreSQL do Video Service em `localhost:5433` |
| `STORAGE_ENDPOINT` | `http://localhost:9000` |
| `STORAGE_PUBLIC_ENDPOINT` | `http://localhost:9000`, usado nas URLs assinadas |
| `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_BUCKET` | credenciais locais do MinIO, bucket `videos` |

Os padrões são os valores de desenvolvimento do `.env.example`. Na AWS, o
deploy gera o arquivo de ambiente a partir dos GitHub Secrets e aponta para os
túneis de [`infrastructure/aws/tunnels`](../../infrastructure/aws/tunnels/README.md).
Nessa rede, o MinIO não é acessível pelo navegador, então o upload por URL
assinada na AWS ainda depende de uma mudança na infraestrutura.

O estado das dependências fica em `/actuator/health`. O `GET /health` continua
disponível para o deploy.

## Testar

Com JDK 21 instalado. O Maven Wrapper baixa o Maven 3.9.11 na primeira
execução; no Windows, use `mvnw.cmd`.

```bash
./mvnw verify
./mvnw test -Dtest=VideoApiTest
./mvnw test -Dtest='VideoApiTest#deletesVideoAndItsFile'
```

Os testes usam H2 em modo PostgreSQL e simulam o MinIO, então não precisam de
Docker. O `./mvnw verify` falha se a cobertura de linhas ficar abaixo de 80%;
o relatório fica em `target/site/jacoco/index.html`.

## Executar

Com as dependências de [`infrastructure`](../../infrastructure/README.md) no
ar, suba o serviço na porta `8081`, que é onde o Job Service o procura
localmente:

```bash
./mvnw spring-boot:run -Dspring-boot.run.arguments=--server.port=8081
```

Somente a imagem:

```bash
docker build -t video-insight/video-service .
docker run --rm -p 8081:8080 video-insight/video-service
```
