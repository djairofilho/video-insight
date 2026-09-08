# Workflows

O workflow `validate-repository.yml` verifica documentação, links locais,
contratos, Docker Compose e presença acidental de secrets.

O arquivo `.github/paths-filter.yaml` centraliza os grupos de caminhos do
monorepo. Futuros pipelines de build e deploy devem reutilizar esses grupos para
executar somente quando o componente correspondente for alterado.

Não há revisão obrigatória, CODEOWNERS ou proteção de branch configurada nesta
etapa.
