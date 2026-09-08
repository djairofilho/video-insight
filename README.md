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

## Documentação

- [Contexto, escopo e requisitos do produto](docs/contexto-produto-videos-ia.md)
- [Registro da decisão arquitetural](docs/decisoes/adr-001-processamento-videos-ia.md)
- [Arquitetura cloud-agnostic](docs/arquiteturas/videos-ia-agnostica.html)
- [Arquitetura AWS](docs/arquiteturas/videos-ia-aws.html)

O enunciado original da disciplina está disponível em
[`Trabalho - Projeto de Software.pdf`](Trabalho%20-%20Projeto%20de%20Software.pdf).
