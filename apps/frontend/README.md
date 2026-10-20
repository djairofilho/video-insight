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
| `/login` | Ponto de entrada do Auth0 (etapa 3) |

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

O Auth0 é integrado em [`src/services/authService.ts`](src/services/authService.ts):

- `setAccessTokenProvider` registra a função que devolve o access token,
  enviado como `Authorization: Bearer` em todas as chamadas.
- `setSessionChecker` informa se há sessão; sem ela, as rotas protegidas
  redirecionam para `/login`.
- Uma resposta `401` leva para `/login` com o aviso de sessão expirada.

Com `VITE_AUTH0_DOMAIN` vazio, as rotas ficam abertas e as chamadas saem sem
token, como os serviços aceitam nesta etapa.

## Configuração

Copie `.env.example` para `.env.local` (ignorado pelo Git):

| Variável | Uso |
|---|---|
| `VITE_API_BASE_URL` | URL do Gateway com `/api/v1`; na AWS, `http://3.227.9.20:8081/api/v1` |
| `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_AUDIENCE` | Auth0; vazio desliga a proteção das rotas |

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
