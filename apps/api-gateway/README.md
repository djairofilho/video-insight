# API Gateway

Ponto único de entrada HTTP para o frontend.

## Responsabilidades

- Encaminhar `/videos` ao Video Service.
- Encaminhar `/jobs` ao Job Service.
- Validar tokens JWT emitidos pelo provedor de autenticação.
- Aplicar CORS, limites de requisição e identificadores de correlação.
- Expor métricas de tráfego, latência e erros.

O Gateway não contém regras de negócio, não acessa bancos e não recebe o
conteúdo dos vídeos. A implementação usa KrakenD Community Edition. Além das
rotas `/health/video`, `/health/jobs` e `/health/processing`, o Gateway publica
as APIs de Vídeos e Jobs sob `/api/v1`. As rotas de negócio usam `no-op` para
preservar os códigos HTTP, corpos e cabeçalhos dos serviços. O CORS aceita
chamadas sem credenciais do navegador; autenticação JWT e limites de requisição
entram em uma etapa posterior.

## Executar

```bash
docker build -t video-insight/api-gateway .
docker run --rm -p 8080:8080 video-insight/api-gateway
```
