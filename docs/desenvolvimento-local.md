# Desenvolvimento local com Auth0

## Quatro comandos

Abra a raiz do projeto e execute primeiro o setup:

```bash
cd /Users/eduardo/Desktop/Insper/video-insight
bash scripts/setup-docker.sh
```

Depois, em três terminais separados, a partir da raiz:

```bash
bash scripts/run-video-service.sh
```

```bash
bash scripts/run-job-service.sh
```

```bash
bash scripts/run-frontend.sh
```

Os três serviços permanecem em primeiro plano; use Ctrl+C para encerrá-los.
Se já houver uma execução antiga, encerre-a no terminal correspondente antes.
Os scripts não matam processos que ocupem as portas. Podem ser chamados por
caminho absoluto de outro diretório: resolvem os arquivos a partir do projeto.

Pré-requisitos: Docker Desktop/Compose v2, JDK 21, Node.js 22.12+ e npm. O setup
abre Docker Desktop no macOS se necessário e aguarda o daemon. Não instala
Docker, Java ou Node. A primeira execução baixa imagens, dependências Maven e
npm e o binário oficial MinIO com SHA-256 verificado; precisa de internet.

## Arquivos locais

- `.env`: bancos, RabbitMQ, MinIO e portas locais. O setup cria a partir de
  `.env.example` somente se não existir. Não substitui senhas existentes.
- `apps/frontend/.env.local`: configuração pública Auth0 e URL da API. O setup
  cria a partir do exemplo se não existir; o script do frontend também verifica
  sua existência.

Os scripts Java reutilizam esse mesmo arquivo para derivar AUTH_ISSUER e
AUTH_AUDIENCE; não é necessário repetir exports em cada terminal.
`run-local-service.sh` é o auxiliar interno compartilhado pelos dois scripts
Java. Não é um quinto comando que você precise executar.

## Credenciais Auth0 já preenchidas

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_AUTH0_DOMAIN=dev-wj6kifnw5uxt2gpk.us.auth0.com
VITE_AUTH0_CLIENT_ID=ni2qNMV1N9PYkxUOqUNaIC5vbgF28BsJ
VITE_AUTH0_AUDIENCE=https://video-insight-api
```

Esses três valores Auth0 já foram fornecidos e configurados. Para obtê-los
novamente: Domain e Client ID ficam em **Applications → Applications → SPA →
Settings**. A audience é **Applications → APIs → API → Settings → Identifier**.
O ID administrativo `6ad928e1b86689f988d9fc98` da API não substitui o Identifier.
O Client Secret da SPA não é usado nem deve ser copiado para o frontend.

## Configuração necessária no painel Auth0

1. Na SPA, cadastre `http://localhost:5173` em **Allowed Callback URLs**,
   **Allowed Logout URLs** e **Allowed Web Origins**.
2. Em **Authentication → Database → Username-Password-Authentication →
   Applications**, habilite a SPA. Deixe **Disable Sign Ups** desligado.
3. Use **New Universal Login** e desabilite a conexão Google para essa SPA.
4. Na API `https://video-insight-api`, abra **Application Access**, edite o
   acesso da SPA e autorize **User-Delegated Access**. Se necessário, use
   **Per-app authorization** e autorize somente essa aplicação. Não é
   necessário acesso M2M/Client Credentials.
5. Confirme RS256 na API. Confira os templates e a configuração de entrega de
   e-mails do Auth0 para testar recuperação de senha e verificação de e-mail.

O último teste real encontrou a SPA sem autorização para a API. Essa alteração
precisa ser salva no tenant; executar os scripts locais não altera o painel.

## Conferir cadastro e login

Abra `http://localhost:5173/videos` sem sessão: deve redirecionar a `/login`.
Clique em **Criar conta** para cadastrar e-mail e senha na página do Auth0.
Use uma conta sua; a senha nunca passa pelo código do Video Insight.
Depois do retorno, confira a lista de vídeos e o botão **Sair**. Saia e entre
novamente em **Entrar com e-mail e senha**. Não há serviço próprio de usuários.

```bash
curl http://localhost:8081/health
curl http://localhost:8082/health
# Esperado sem token: HTTP 401
curl -i http://localhost:8081/api/v1/videos
```

Sem configuração Auth0 ou sem sessão, a SPA bloqueia as rotas protegidas.
Nome completo não é coletado pelo formulário padrão implementado; consulte
[as limitações e instruções Auth0](login-auth0.md).

## Portas e processamento

| Componente | Endereço |
| --- | --- |
| Frontend | <http://localhost:5173> |
| Video Service | <http://localhost:8081> |
| Job Service | <http://localhost:8082> |
| MinIO API | <http://127.0.0.1:19000> |
| MinIO console | <http://localhost:9001> |
| RabbitMQ admin | <http://localhost:15672> |
| PostgreSQL Video / Job | localhost:5433 / localhost:5434 |

O MinIO usa 19000 no host para não conflitar com PHP-FPM na porta 9000.
As URLs assinadas usam a mesma porta configurada em `.env`.

Esses quatro scripts permitem testar autenticação, vídeos, upload e API de
jobs. O worker Python não está incluído: transcrição/resumo/capítulos só serão
executados quando o Processing Service for iniciado com as chaves Groq/Gemini.
Sem worker, um job criado pode permanecer na fila.

Para encerrar as dependências sem apagar dados:

```bash
docker compose --env-file .env -f infrastructure/compose.yaml down
```
