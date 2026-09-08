# API Gateway

Ponto único de entrada HTTP para o frontend.

## Responsabilidades

- Encaminhar `/videos` ao Video Service.
- Encaminhar `/jobs` ao Job Service.
- Validar tokens JWT emitidos pelo provedor de autenticação.
- Aplicar CORS, limites de requisição e identificadores de correlação.
- Expor métricas de tráfego, latência e erros.

O Gateway não conterá regras de negócio, não acessará bancos e não receberá o
conteúdo dos vídeos. A tecnologia será escolhida antes da implementação.
