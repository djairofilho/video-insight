# Frontend

Interface web do Video Insight. O usuário envia um MP4, escolhe as operações,
acompanha o processamento e consulta transcrição, resumo e capítulos com
navegação por timestamp.

Usa React 19, TypeScript, Vite, React Compiler, MUI e React Router. Conversa
somente com o API Gateway; o arquivo de vídeo vai direto do navegador para o
armazenamento pela URL assinada, sem passar pelo backend.

## Telas

| Rota | Tela |
|---|---|
| `/videos` | Lista com paginação por cursor e exclusão |
| `/videos/new` | Validação local (MP4, 100 MB, 10 min) e envio com progresso |
| `/videos/:videoId` | Dados do vídeo, escolha das operações e processamentos anteriores |
| `/jobs/:jobId` | Progresso por polling, cancelamento e nova tentativa |
| `/jobs/:jobId/result` | Player, resumo, capítulos com diagramas, transcrição e exportação |
| `/login` | Entrada pelo Auth0 Universal Login |

## Organização

```text
src/
  app/         rotas, tema e composição
  pages/       uma tela por rota, carregada sob demanda
  components/  componentes de layout, vídeo, job e resultado
  hooks/       carregamento, polling do job e envio do vídeo
  services/    cliente HTTP e chamadas ao Gateway
  types/       modelos equivalentes aos contratos (snake_case)
  utils/       formatação e validações puras
  mocks/       Gateway simulado com MSW (testes e modo de demonstração)
```

Decisões principais:

- O polling agenda a próxima consulta só depois da resposta, para em
  `completed`, `failed` ou `cancelled` e é cancelado ao sair da tela.
- A criação do job envia `Idempotency-Key`. A mesma chave é reaproveitada
  apenas quando a requisição falha sem resposta do servidor.
- Resumo e textos dos capítulos são Markdown sanitizado com `rehype-sanitize`.
  Blocos de capítulo desconhecidos aparecem como conteúdo indisponível.
- Erros mostram uma mensagem compreensível e o `correlation_id`; o console
  registra `code` e `correlation_id` de cada falha da API.

## Autenticação

O SDK oficial Auth0 gerencia login, logout e tokens em memória. A aplicação usa
Authorization Code com PKCE e solicita access tokens para a audience da API.
As rotas aguardam o carregamento da sessão antes de redirecionar ao login.
O cliente HTTP anexa o bearer token e trata falhas de renovação e respostas 401.

Consulte o [guia de configuração e deploy](../../docs/autenticacao-e-deploy.md).
O build de produção exige as três variáveis Auth0 e uma API HTTPS. As rotas protegidas exigem sessão também em desenvolvimento; configuração
ausente bloqueia o acesso e mostra o erro no login.

## Configuração

Copie `.env.example` para `.env.local` (ignorado pelo Git):

| Variável | Uso |
|---|---|
| `VITE_API_BASE_URL` | URL HTTPS pública do Gateway com `/api/v1` em produção |
| `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_AUDIENCE` | Configuração pública Auth0; obrigatória em produção |

Variáveis `VITE_*` vão para o bundle do navegador: não coloque segredos nelas.

## Executar

```bash
npm install
npm run dev        # usa o Gateway de VITE_API_BASE_URL
npm run dev:local  # serviços rodando na máquina (Video 8081, Job 8082)
npm run dev:mock   # Gateway simulado no navegador, com um vídeo de exemplo
```

No `dev:local`, o servidor do Vite encaminha `/api/v1/videos` ao Video Service
e `/api/v1/videos/{id}/jobs` e `/api/v1/jobs` ao Job Service, como o Gateway
faz na AWS. Como subir os serviços está em
[`tests/end-to-end/README.md`](../../tests/end-to-end/README.md).

O modo `dev:mock` não precisa dos serviços nem de `.env`: um job novo avança
uma etapa a cada consulta até concluir.

## Testar

```bash
npm run lint
npm test
npm run test:coverage
npm run build
```

Os testes usam Vitest, Testing Library e MSW. Eles renderizam as rotas reais
contra o Gateway simulado de [`src/mocks/handlers.ts`](src/mocks/handlers.ts)
e cobrem utilitários, cliente HTTP, upload pela URL assinada, polling,
componentes e os fluxos de envio, criação de job, nova tentativa,
cancelamento, resultado, exportação e redirecionamento para o login.

## Deploy na EC2

O job `deploy-frontend` de `.github/workflows/deploy-aws.yml` compila e testa a
SPA e envia uma imagem Nginx à máquina definida por `AWS_FRONTEND_HOST`.
`AWS_FRONTEND_PORT` usa 8081 por padrão. O Dockerfile recebe `dist/` já compilado;
não execute `vite dev` nem `vite preview` como servidor de produção.
As configurações e os passos de HTTPS estão no
[guia de deploy](../../docs/autenticacao-e-deploy.md).

Veja o [passo a passo de login e cadastro com Auth0](../../docs/login-auth0.md),
sem serviço próprio de usuários.
