# Primeira entrega: definição, arquitetura e deploy

## Ideia do projeto

O Video Insight transforma vídeos informativos em conteúdo pesquisável. O
usuário envia um MP4 e recebe transcrição com timestamps, resumo e capítulos
automáticos. O processamento ocorre em segundo plano para que uploads e tarefas
longas não bloqueiem a interface.

O MVP está limitado a vídeos de até 10 minutos e 100 MB. Streaming, edição
completa, tradução, dublagem e treinamento de modelos ficam fora desta etapa.

## Serviços

| Serviço | Responsabilidade | Tecnologia | Deploy |
|---|---|---|---|
| Video Service | Metadados, propriedade e acesso ao arquivo | Java 21 e Spring Boot | EC2 de Matheus Pereira |
| Job Service | Estado, progresso, tentativas e resultados dos jobs | Java 21 e Spring Boot | EC2 de Marcus |
| Processing Service | FFmpeg, transcrição, resumo e capítulos | Python 3.12 e FastAPI | EC2 de Eduardo Marcelino |

O KrakenD, na máquina de Djairo, é o ponto único de entrada HTTP. Os três
serviços expõem `GET /health` nesta entrega para comprovar build, deploy e
comunicação. As APIs de negócio já estão definidas em OpenAPI, mas serão
implementadas nas próximas entregas.

## Arquitetura

[Abrir diagrama interativo da arquitetura AWS](arquiteturas/videos-ia-aws.html)

![Arquitetura AWS do Video Insight](arquiteturas/videos-ia-aws.png)

O fluxo planejado é:

1. O frontend chama o KrakenD.
2. O Gateway encaminha vídeos ao Video Service e jobs ao Job Service.
3. Video Service alcança seu PostgreSQL e o MinIO por túneis SSH persistentes.
4. Job Service alcança seu PostgreSQL e o RabbitMQ pelos mesmos túneis e publica
   `processing.requested`.
5. Processing Service acessa RabbitMQ e MinIO pelos túneis, usa um adapter de IA
   e publica eventos de progresso, conclusão ou falha.
6. Prometheus coleta inicialmente suas próprias métricas e o Grafana recebe a
   fonte de dados pronta; a instrumentação dos serviços evolui com a aplicação.

O Processing Service não acessa PostgreSQL. Ele se integra a RabbitMQ, MinIO e
ao provedor de IA; o Job Service persiste o estado comunicado pelos eventos.

## Distribuição nas máquinas AWS

| Máquina | Componente | Porta do produto |
|---|---|---|
| Djairo | KrakenD | `8081` |
| Matheus Pereira | Video Service | `8081` |
| Marcus | Job Service | `8081` |
| Eduardo Marcelino | Processing Service | `8081` |
| Ruan | Dois PostgreSQL, RabbitMQ e MinIO | `5433`, `5434`, `5672`, `9000` |
| Leonardo Moretti | Prometheus e Grafana | `9090`, `3000` |

As chamadas HTTP usam os endereços privados da VPC. Como as portas de dados são
bloqueadas pelo Security Group e o grupo não pode alterá-lo, PostgreSQL,
RabbitMQ e MinIO são alcançados por túneis SSH persistentes na porta `22`.
Senhas e chaves privadas não ficam no repositório.

Para acesso pela internet, o KrakenD usa `http://3.227.9.20:8081`. A porta `80`
continua bloqueada na camada de rede da AWS. A exposição pública de `8081` nas
máquinas dos serviços deve ser restringida ao Gateway por uma identidade AWS
com permissão para alterar grupos de segurança.

## Deploy automático

O workflow [`.github/workflows/deploy-aws.yml`](../.github/workflows/deploy-aws.yml)
roda em pushes para `main`. Filtros de caminho identificam o componente
alterado, constroem e testam sua imagem, copiam a imagem por SSH, substituem
somente o contêiner do Video Insight e confirmam o endpoint de saúde.

O ambiente compartilhado e a observabilidade também têm deploy seletivo quando
seus respectivos diretórios mudam. O workflow de validação continua verificando
Markdown, links, contratos, Docker Compose, imagens dos serviços e secrets.

## Evidências de conclusão

- Monorepo privado publicado em `djairofilho/video-insight`.
- Estrutura dos três serviços criada e executável.
- Contratos OpenAPI e JSON Schema versionados.
- Ambientes local e AWS descritos como código.
- Diagrama AWS validado deterministicamente e revisado visualmente.
- CI e CD configurados com filtros por diretório.

Os links das execuções de CI/CD e o estado final das instâncias devem ser
consultados na página de Actions do repositório, que mantém o histórico de cada
deploy.

## Atendimento ao enunciado

| Requisito da etapa | Evidência no repositório | Situação nesta entrega |
|---|---|---|
| Ideia do projeto e escopo | [Contexto do produto](contexto-produto-videos-ia.md) e ADR 001 | Definido |
| Três ou mais serviços | `services/video-service`, `services/job-service` e `services/processing-service` | Estrutura criada |
| Diagrama de arquitetura | [Diagrama AWS](arquiteturas/videos-ia-aws.html) e [diagrama cloud-agnostic](arquiteturas/videos-ia-agnostica.html) | Disponível |
| Comunicação entre serviços | KrakenD, REST, RabbitMQ e eventos versionados | Definida e parcialmente comprovada por health checks |
| Bancos e dependências | PostgreSQL separado por serviço, RabbitMQ e MinIO | Definidos em Docker Compose e AWS |
| Repositórios e execução | Monorepo com Dockerfiles e READMEs por componente | Configurado |
| Deploy automático | [Workflow de deploy AWS](../.github/workflows/deploy-aws.yml) | Configurado para `main` |
| Testes automatizados | Testes iniciais dos endpoints de saúde e validações no CI | Base criada; cobertura evolui na etapa 2 |
| Secrets | GitHub Secrets, GitHub Variables e `.env.example` sem credenciais reais | Configurado |

Autenticação e autorização com Auth0, monitoramento completo, testes de carga e
os testes de integração da aplicação estão previstos para as próximas etapas,
conforme o cronograma do enunciado. Nesta primeira entrega, a arquitetura já
reserva os pontos de integração necessários.

## Padrões de projeto previstos

As fronteiras definidas nesta entrega permitem aplicar os padrões exigidos pela
disciplina em problemas reais do domínio:

- **API Gateway:** ponto único de entrada e roteamento;
- **Adapter:** isolamento do provedor de transcrição e resumo;
- **Strategy:** seleção da implementação de transcrição ou de inteligência de
  conteúdo;
- **Factory:** criação de jobs, eventos e adaptadores conforme a operação;
- **Singleton:** componentes compartilhados de configuração e infraestrutura,
  quando a implementação exigir uma única instância por aplicação;
- **Idempotent Consumer:** proteção contra reentrega de mensagens;
- **Retry e DLQ:** tratamento de falhas temporárias e mensagens que não podem
  ser processadas.

## Próximas etapas

1. Implementar as operações de vídeo, jobs, upload e processamento previstas nos
   contratos OpenAPI.
2. Expandir os testes unitários, de integração, contrato e ponta a ponta,
   buscando a cobertura mínima exigida na disciplina.
3. Integrar Auth0 para autenticação e autorização, sem criar um serviço próprio
   de identidade.
4. Implementar o frontend, testes de carga e instrumentação completa com
   Prometheus e Grafana.
