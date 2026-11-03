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

O job `deploy-frontend` publica a SPA Vite/React no projeto Vercel após as
validações. O build remoto recebe as configurações públicas do ambiente
Production da Vercel; a publicação usa `VERCEL_TOKEN` e os IDs do projeto/equipe.
Os serviços AWS continuam entregues como imagens por SSH, com rollback.
O workflow também provisiona HTTPS de objetos, coleta restrita, túneis,
dashboards e alertas, preservando volumes e o ledger de consumo do worker.
A lista completa de configurações está no
[guia de autenticação e deploy](../../docs/autenticacao-e-deploy.md).
