# API Gateway

Ponto único de entrada HTTP para o frontend.

## Responsabilidades

- Encaminhar `/videos` ao Video Service.
- Encaminhar `/jobs` ao Job Service.
- Validar tokens JWT emitidos pelo provedor de autenticação.
- Aplicar CORS, limites de requisição e identificadores de correlação.
- Expor métricas de tráfego, latência e erros.

O Gateway não conterá regras de negócio, não acessará bancos e não receberá o
conteúdo dos vídeos. A implementação escolhida é o KrakenD Community Edition.
Nesta primeira entrega, as rotas `/health/video`, `/health/jobs` e
`/health/processing` comprovam a comunicação entre as máquinas AWS.

## Executar

```bash
docker build -t video-insight/api-gateway .
docker run --rm -p 8080:8080 video-insight/api-gateway
```
