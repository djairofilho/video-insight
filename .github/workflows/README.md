# Workflows

O workflow `validate-repository.yml` verifica documentação, links locais,
contratos, Docker Compose, imagens dos serviços e presença acidental de
secrets.

O workflow `deploy-aws.yml` entrega os componentes alterados às cinco instâncias
EC2 após pushes para `main`. Ele também pode ser iniciado manualmente para
refazer o deploy completo. Nos três serviços, o workflow também instala e
reinicia os túneis SSH usados para acessar as dependências na máquina de Ruan.

O arquivo `.github/paths-filter.yaml` centraliza os grupos de caminhos do
monorepo. O CI e o CD usam filtros para executar somente quando o componente
correspondente for alterado.

Não há revisão obrigatória, CODEOWNERS ou proteção de branch configurada nesta
etapa.

O job `deploy-frontend` compila a SPA Vite/React e publica uma imagem Nginx por
SSH na EC2 definida por `AWS_FRONTEND_HOST`. Ele executa testes e verifica as
rotas da SPA antes e depois da troca, com restauração do contêiner anterior em
caso de falha. As configurações Auth0 e URLs são fornecidas por Variables;
o frontend reutiliza os secrets SSH existentes. A lista completa está no
[guia de autenticação e deploy](../../docs/autenticacao-e-deploy.md).
