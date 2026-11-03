# API Gateway

Ponto único de entrada HTTP para o frontend.

## Responsabilidades

- Encaminhar `/videos` ao Video Service.
- Encaminhar `/jobs` ao Job Service.
- Encaminhar bearer tokens para validação independente em cada serviço Java.
- Aplicar CORS, limites de requisição e identificadores de correlação.
- Expor métricas de tráfego, latência e erros.

O Gateway não contém regras de negócio, não acessa bancos e não recebe o
conteúdo dos vídeos. A implementação usa KrakenD Community Edition. Além das
rotas `/health/video`, `/health/jobs` e `/health/processing`, o Gateway publica
as APIs de Vídeos e Jobs sob `/api/v1`. As rotas de negócio usam `no-op` para
preservar os códigos HTTP, corpos e cabeçalhos dos serviços. O CORS de produção aceita a origem HTTPS do Pages, definida por
`scripts/render_deployment.py` no workflow. Os serviços Java validam JWT Auth0 e verificam
a propriedade de cada recurso. Limites de requisição permanecem uma etapa futura.

## Executar

```bash
python ../../scripts/render_deployment.py gateway --example
docker build -t video-insight/api-gateway .
docker run --rm -p 8080:8080 video-insight/api-gateway
```

O exemplo usa somente hosts locais para validar a configuração. Em produção,
execute o renderer sem `--example`, com os hosts privados fornecidos por Secrets.
O arquivo versionado é `krakend.json.template`; `krakend.json` é gerado e ignorado.
