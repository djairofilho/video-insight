# Video Insight

Plataforma de processamento assíncrono de vídeos com IA desenvolvida para a
disciplina de Projeto de Software.

O usuário envia um vídeo e recebe uma transcrição com timestamps, um resumo e
capítulos automáticos. O MVP aceita arquivos MP4 de até 10 minutos e 100 MB.

## Microsserviços

- **Video Service:** gerencia metadados, propriedade, validação e acesso ao
  arquivo.
- **Job Service:** gerencia solicitações de processamento, estados, progresso,
  tentativas e eventos.
- **Processing Service:** extrai o áudio, transcreve e produz resumo e capítulos.

## Organização do monorepo

```text
apps/           frontend e API Gateway
services/       microsserviços do produto
contracts/      contratos REST e de eventos
infrastructure/ dependências locais e observabilidade
tests/          testes entre componentes e de carga
docs/           produto, decisões e arquiteturas
```

Cada componente tem um README próprio com sua responsabilidade e seus limites.
Video Service e Job Service usam Java 21 com Spring Boot, o Processing Service
usa Python 3.12 com FastAPI e o API Gateway usa KrakenD Community Edition. O
frontend usa React, TypeScript e Vite.

## Documentação

- [Contexto, escopo e requisitos do produto](docs/contexto-produto-videos-ia.md)
- [Relatório da primeira entrega](docs/entrega-1.md)
- [Registro da decisão arquitetural](docs/decisoes/adr-001-processamento-videos-ia.md)
- [Arquitetura cloud-agnostic](docs/arquiteturas/videos-ia-agnostica.html)
- [Arquitetura AWS](docs/arquiteturas/videos-ia-aws.html)
- [Contratos entre componentes](contracts/README.md)
- [Ambiente local](infrastructure/README.md)
- [Autenticação Auth0 e publicação AWS / EC2](docs/autenticacao-e-deploy.md)
- [Deploy nas máquinas AWS](infrastructure/aws/README.md)

O enunciado original da disciplina está disponível em
[`Trabalho - Projeto de Software.pdf`](Trabalho%20-%20Projeto%20de%20Software.pdf).

Veja o [passo a passo de login e cadastro com Auth0](docs/login-auth0.md),
sem serviço próprio de usuários.

Para iniciar cada componente, siga os [quatro scripts de desenvolvimento local](docs/desenvolvimento-local.md).
