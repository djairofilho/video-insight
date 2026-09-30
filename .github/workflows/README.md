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
