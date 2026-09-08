# ADR 001: processamento de vídeos com IA

- **Status:** aceita
- **Data:** 7 de setembro de 2026
- **Decisores:** grupo do Projeto de Software

## Contexto

O grupo precisava escolher um produto com boa aderência ao enunciado, fronteiras
arquiteturais naturais, escopo executável e uma demonstração clara. O
processamento de vídeos com IA reúne essas características, desde que os limites
do MVP sejam respeitados.

## Decisão

Desenvolver o **Video Insight**, uma plataforma de processamento assíncrono de
vídeos com IA.

O MVP receberá arquivos MP4 de até 10 minutos e 100 MB e produzirá:

1. transcrição em português com timestamps;
2. resumo do conteúdo;
3. capítulos com título, início e fim.

A solução terá, no mínimo, três microsserviços:

- **Video Service:** metadados, propriedade, validação e URLs assinadas;
- **Job Service:** criação, estado, progresso, idempotência e eventos dos jobs;
- **Processing Service:** FFmpeg, transcrição, resumo, capítulos e artefatos.

O frontend acessará os serviços por um API Gateway. O processamento longo será
disparado por mensageria e não manterá requisições HTTP abertas.

As tecnologias iniciais são Java 21 com Spring Boot para Video Service e Job
Service, Python 3.12 com FastAPI para Processing Service, KrakenD Community
Edition no Gateway, RabbitMQ para mensageria, MinIO para objetos e PostgreSQL
separado para cada serviço de negócio.

O Processing Service continuará sendo um único microsserviço, dividido
internamente em dois módulos que podem ser desenvolvidos em paralelo:

- **Mídia e transcrição:** FFmpeg, normalização do áudio, Speech-to-Text,
  timestamps e exportação em TXT ou SRT;
- **Inteligência de conteúdo:** resumo, identificação de tópicos e geração de
  capítulos.

Video Service e Job Service permanecerão separados. O primeiro gerencia o
arquivo e sua propriedade; o segundo gerencia cada execução, seus estados,
tentativas e eventos.

## Justificativa

- O pipeline de vídeo torna mensageria, workers e progresso observável partes
  essenciais do produto, e não requisitos artificiais.
- A separação entre vídeo, job e processamento permite deploy e escalabilidade
  independentes.
- A demonstração evidencia upload, consistência eventual, transições de estado,
  resultados de IA e métricas operacionais.
- O escopo limitado mantém o risco compatível com o prazo da disciplina.

## Consequências

### Positivas

- Arquitetura distribuída fácil de justificar e demonstrar.
- Problema adequado a processamento assíncrono e escalabilidade horizontal.
- Possibilidade de aplicar Adapter, Pipeline, Retry, Idempotent Consumer e DLQ
  em problemas reais do domínio.

### Negativas

- Maior consumo de CPU, memória, disco e object storage.
- Testes de integração mais lentos e dependentes de arquivos de mídia.
- Custo e latência variáveis caso sejam usados provedores externos de IA.
- Mais casos de falha por codec, formato, duração e interrupção do worker.

## Restrições de escopo

Não fazem parte do MVP:

- streaming e transmissão ao vivo;
- editor de vídeo completo;
- tradução e dublagem;
- treinamento de modelos;
- suporte irrestrito a formatos e codecs;
- geração automática de cortes para redes sociais.

Cortes automáticos poderão ser implementados apenas como bônus, depois que o
fluxo principal estiver estável e testado.

## Decisões pendentes

- Provedor local ou externo para transcrição e resumo.
- Política de retenção dos vídeos e artefatos.
- Semântica exata de cancelamento durante uma etapa em execução.

## Documentos relacionados

- [Contexto do produto](../contexto-produto-videos-ia.md)
- [Arquitetura cloud-agnostic](../arquiteturas/videos-ia-agnostica.html)
- [Arquitetura AWS](../arquiteturas/videos-ia-aws.html)
