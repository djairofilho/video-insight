# Entrega 4: validação e apresentação

## Estado da entrega

Ambiente funcional publicado em <https://video-insight-ruby.vercel.app>.
Auth0 e propriedade por usuário estão ativos. Upload, processamento real e
isolamento entre duas contas passaram pelos testes. A entrega ainda precisa da
execução do pipeline novo após publicação autorizada do código e da conclusão
da limpeza dos artefatos derivados na exclusão (RF10/RN06).

## Evidências de 2 de novembro de 2026

| Verificação | Resultado |
| --- | --- |
| Video Service com PostgreSQL 17 real | 37 testes, cobertura de linhas 96,74% |
| Job Service com PostgreSQL 17 real | 52 testes, cobertura de linhas 97,50% |
| Processing com RabbitMQ/MinIO reais e FFmpeg | 192 testes, cobertura 99,47% |
| Frontend | lint, 82 testes em 12 arquivos e build de produção passaram |
| Testes ponta a ponta publicados | 19 passaram em 107,86 s |
| Upload próximo de 100 MiB | 104.856.576 bytes, HTTP 200, 112,28 s pela Vercel |
| Reprodução Range | HTTP 206, bytes 0–1023, `private, no-store`, cache MISS |
| Download sem assinatura | HTTP 403 |
| Carga autenticada | 50 consultas, 5 clientes, 0 erros, p50 182,05 ms, p95 1.464,47 ms |
| Prometheus | Video, Job e Processing com scrape `up` |
| Grafana | dashboard `video-insight`, seis painéis provisionados |
| Gitleaks | sem achados; chave sintética adicional foi detectada |
| Contratos e workflow | JSON Schema, OpenAPI e actionlint passaram |

O vídeo próprio de teste tem 23,27 segundos, fala em português e 5.420.162 bytes.
Gerou cinco segmentos com timestamps, resumo de 459 caracteres e um capítulo.
Groq usou `whisper-large-v3-turbo`; resumo e capítulos usaram
`gemini-3.5-flash-lite`. Exportações TXT, SRT e JSON retornaram HTTP 200.
O arquivo de 100 MiB foi validado em upload, confirmação e Range; o processamento
de IA foi validado com o vídeo curto, não com o arquivo preenchido de 100 MiB.

A carga mede consultas autenticadas pela internet, não capacidade máxima nem
vazão dos provedores de IA. Os testes Java usam banco real, mas substituem
RabbitTemplate, cliente Video e storage por mocks. A suíte publicada cobre esses
hops com serviços reais. A recuperação do broker usa um RabbitMQ descartável,
sem parar o broker da aplicação: parada/retorno, reconexão, reentrega idempotente
e DLQ passaram. Expiração é coberta pelos validadores JWT Java; não se aguardou
um token Auth0 real expirar. A validação visual de reprodução foi informada pelo
titular, que pediu para dispensar sua repetição.

## Versões implantadas na validação manual

Base Git: `f2432909036be25ae580b3e06caad70ce35f2465`, com alterações locais
preservadas e ampliadas. Essas evidências precedem os commits do PR de publicação.

- Video, Job e KrakenD: `delivery4-20261102-fe9c495a5e44`.
- Processing: `delivery4-20261102-worker-c4fd48d519c4`.
- Nginx de entrada: `nginx:1.29-alpine`, configuração em
  `infrastructure/aws/edge/proxy.conf`.
- Frontend: produção Vercel `video-insight-oeealb4q4-djairos-projects.vercel.app`,
  alias `video-insight-ruby.vercel.app`.
- Prometheus `v3.5.0` e Grafana `12.1.0`, com configuração atualizada e volumes
  existentes preservados.

As tags locais identificam os binários e fontes enviados, não commits remotos.
O release inclui hashes das fontes e da configuração KrakenD. Contêineres
anteriores continuam disponíveis para rollback. O Job está estável com 512 MiB;
os reinícios anteriores foram causados por OOM no limite de 320 MiB.

## Roteiro de demonstração de 5 minutos

1. **0:00–0:45:** abrir a URL pública e entrar pelo Auth0. Explicar `sub` e
   autenticação independente em Video e Job.
2. **0:45–1:30:** enviar um MP4 curto próprio com fala e confirmar o upload.
   Mostrar o progresso e iniciar transcrição, resumo e capítulos.
3. **1:30–2:30:** explicar a requisição REST síncrona Job → Video, o outbox,
   publisher confirms, RabbitMQ e o processamento assíncrono. Mostrar um
   resultado já concluído se o provedor demorar.
4. **2:30–3:15:** navegar pelos timestamps/capítulo, reproduzir e exportar
   TXT, SRT e JSON. Mostrar os modelos registrados no resultado.
5. **3:15–4:00:** mostrar falha de mídia inválida, retry e cancelamento.
   Apresentar a evidência dos dois jobs reais em paralelo e das duas contas.
6. **4:00–5:00:** abrir Grafana por túnel, mostrar os três scrapes, carga,
   cobertura e os gates do CI. Explicitar as pendências abaixo.

Não use senhas, tokens, URLs assinadas nem chaves de IA em slides ou capturas.
Não exclua vídeos existentes para demonstrar limpeza; use recursos de teste.

## Padrões concretos

- **Strategy:** `Transcriber`, `Summarizer` e `ChapterWriter` são Protocols
  injetados em `ProcessingPipeline`. Em produção entram `GroqTranscriber`,
  `AgentSummarizer` e `AgentChapterWriter`; testes usam estratégias falsas sem
  alterar a sequência do pipeline.
- **Factory:** `create_transcriber` escolhe a fábrica do registro `_PROVIDERS`
  pela configuração `transcription_provider`. `create_content_writers` cria o
  modelo Gemini e os dois agentes com seus limites. Provedor desconhecido ou
  chave ausente gera erro explícito de configuração. Hoje há um provedor de
  produção por fábrica; não se afirma que existam várias alternativas prontas.
- **Singleton:** `get_settings`, com `@lru_cache`, reutiliza a configuração por
  processo Python. No Java, os beans Spring, como `S3Client` e `VideoClient`,
  têm escopo singleton por contexto. Não são singletons globais entre máquinas.

## Pendências e limites

1. **CI/CD remoto:** o código novo continua local por instrução do titular.
   O `VERCEL_TOKEN` já foi cadastrado e os tokens anteriores da entrega foram
   revogados. O comando do workflow foi validado localmente com CLI 65.9.0 e
   esse token: build remoto e publicação em produção concluídos. É necessário
   publicar os commits autorizados e executar o workflow novo no GitHub.
   Não se usa a execução antiga como evidência verde. O token expira em 30 dias.
2. **RF10/RN06:** `VideoService.delete` remove original e metadados, mas não
   agenda a remoção de `artifacts/jobs/{job_id}/attempt-*` nem de `job_results`.
   Os testes atuais de exclusão comprovam a remoção do original, não dos
   derivados. Falta um fluxo durável de exclusão com idempotência e proteção
   contra jobs que terminem depois da solicitação. Não houve limpeza manual de
   dados existentes para ocultar essa lacuna.
3. **TLS na origem:** o navegador usa HTTPS; Vercel → AWS e hops internos usam
   HTTP. O bearer trafega sem TLS nesse trecho. Veja o
   [guia de implantação](autenticacao-e-deploy.md).
4. **Operação:** não há alertas de negócio, limpeza automática da DLQ ou garantia
   de interrupção imediata de uma chamada de IA ao cancelar. O estado cancelado
   é protegido contra eventos tardios. Cotas e indisponibilidade de Groq/Gemini
   continuam sendo dependências externas.
5. **Dependências frontend:** `npm ci` reporta 12 vulnerabilidades moderadas.
   Não foi aplicado upgrade forçado que pudesse quebrar a entrega. A revisão
   dessas dependências deve ser feita com teste de regressão próprio.
6. **Upload no limite:** 112 s deixa pouca margem para conexões lentas.
   O limite do produto foi mantido. Para redes mais lentas, avaliar upload
   multipart/resumível ou TLS direto na origem, com teste real do limite.

## Checklist de aceite

- [x] Novo tenant acessível, SPA, API RS256 e grant delegado configurados.
- [x] Variáveis Vercel/GitHub e autenticação AWS alinhadas.
- [x] API sem token e com token inválido retorna 401.
- [x] Dois usuários separados; IDs e operações cruzadas retornam 404.
- [x] Upload próximo de 100 MiB, Range, query S3 e cache privado validados.
- [x] Fluxo real com transcrição, resumo, capítulos e três exportações.
- [x] Falha, retry, cancelamento, idempotência e concorrência validados.
- [x] Cobertura mínima de 80% nos três serviços.
- [x] Outbox confirma publicação; falhas transitórias permitem reentrega.
- [x] Monitoramento e teste de carga com resultados registrados.
- [x] Documentação e roteiro atualizados em português.
- [ ] Execução remota verde do pipeline novo após publicação autorizada.
- [ ] Exclusão durável dos artefatos derivados e resultados.

## Plano de commits, sem execução

Há responsabilidades de configuração/build, backend, processamento, frontend,
testes e documentação. A divisão abaixo segue `organize-atomic-commits` e
`conventional-commit`; testes ligados à correção ficam junto dela.

1. `fix(storage): preserve signed uploads through the https proxy`
   Inclui proxy frontend, rewrites, Nginx e testes da assinatura. As camadas
   ficam juntas porque o Host só é preservado com a cadeia completa.
2. `fix(messaging): confirm publication and recover transient deliveries`
   Inclui outbox Java, recuperação Python e testes de ack, nack, retorno,
   reentrega e reinício do broker. Resultado: não marcar publicação sem entrega
   confirmada nem descartar solicitação por indisponibilidade transitória.
3. `feat(observability): monitor application services in prometheus`
   Inclui métricas Java/Python, restrição de rede, testes e painel provisionado.
4. `ci(deploy): gate aws and vercel releases on full validation`
   Inclui workflows, deploy com rollback, teste do helper e exceção específica
   Gitleaks. Depende da cadeia de proxy do primeiro commit.
5. `test(e2e): verify authenticated users and bounded load`
   Inclui fixtures, isolamento entre contas, download sem bearer e carga.
6. `docs(delivery): record deployment evidence and acceptance gaps`
   Inclui exemplos Auth0, guias locais/AWS, relatório, roteiro e checklist.

O hunk `maxWorkers: 2` do Vite pertence à estabilidade dos testes do frontend;
revise-o separadamente dos hunks do proxy antes de preparar o primeiro commit.
