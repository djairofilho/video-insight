# Login e cadastro com Auth0

O Auth0 hospeda os formulários de cadastro, login e recuperação de senha.
A SPA não recebe senhas, não cria usuários pela Management API e não mantém
um serviço próprio de usuários. Os serviços Java validam o access token e
associam vídeos e jobs ao identificador `sub`.

## Configurar o painel

1. Em **Authentication → Database**, abra `Username-Password-Authentication`.
   Se não existir, crie uma conexão de banco hospedada pelo Auth0 com esse nome.
   Não configure banco customizado da aplicação.
2. Em **Applications** dessa conexão, habilite a SPA `Video Insight Frontend`.
3. Confirme que **Disable Sign Ups** está desligado, para permitir cadastro.
4. Em **Authentication → Social → Google → Applications**, desabilite Google
   para essa SPA, se estiver habilitado. Não é necessário excluir a conexão.
5. Em **Branding → Universal Login**, use a experiência **New Universal Login**.
   O botão **Entrar com e-mail e senha** solicita a conexão de banco; o botão
   **Criar conta** usa a mesma conexão com `screen_hint=signup`.
6. Em **Applications → Applications → Video Insight Frontend → Settings**,
   confirme Domain `dev-wj6kifnw5uxt2gpk.us.auth0.com` e Client ID
   `ni2qNMV1N9PYkxUOqUNaIC5vbgF28BsJ`.
7. Cadastre `http://localhost:5173` nos três campos **Allowed Callback URLs**,
   **Allowed Logout URLs** e **Allowed Web Origins**. Salve.
8. Em **Applications → APIs → sua API**, copie **Identifier** e confirme **RS256**.
   O Identifier é a audience, não o Client ID de outra aplicação.
9. Nessa API, abra **Application Access → Edit** e autorize **User-Delegated
   Access** para a SPA `Video Insight Frontend` (Client ID
   `ni2qNMV1N9PYkxUOqUNaIC5vbgF28BsJ`). Mantenha autorização por aplicação;
   não é necessário liberar todas as aplicações nem ativar Client Access/M2M.
   Se a política estiver em **No apps allowed**, altere para **Per-app
   authorization** e autorize somente essa SPA.

O teste real do fluxo identificou que a SPA ainda não tinha esse acesso à API
`https://video-insight-api`: o Auth0 retornava `Client is not authorized to
access resource server`. Essa permissão precisa ser salva no tenant antes
que o login real possa ser concluído.

A conexão configurada no código se chama `Username-Password-Authentication`.
Se sua conexão tiver outro nome, ajuste `AuthLoginButton.tsx` para corresponder.
A desativação de provedores sociais é uma configuração do tenant, não uma
regra que o frontend possa impor sozinho.

Configure a política de senhas na conexão e confira os templates de verificação
de e-mail e recuperação de senha em **Branding → Email Templates**. Entrega de
e-mails depende da configuração do provedor no Auth0; os recursos de teste do
tenant não substituem uma configuração de entrega para uso público. A emissão
ou exigência de verificação de e-mail deve ser uma decisão explícita do tenant.

## Executar localmente

Copie `apps/frontend/.env.example` para `apps/frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_AUTH0_DOMAIN=dev-wj6kifnw5uxt2gpk.us.auth0.com
VITE_AUTH0_CLIENT_ID=ni2qNMV1N9PYkxUOqUNaIC5vbgF28BsJ
VITE_AUTH0_AUDIENCE=IDENTIFIER_EXATO_DA_API
```

Substitua `IDENTIFIER_EXATO_DA_API` pelo campo Identifier do painel. Se o valor
cadastrado for `https://video-insight-api`, use exatamente esse valor.
O Client Secret da SPA não é utilizado. Não é necessário cliente OAuth Google,
credenciais Google nem novos Secrets no GitHub.

```bash
cd apps/frontend
npm ci
npm run dev:local -- --port 5173 --strictPort
```

Para usar a API, os serviços Java locais precisam de suas dependências e de:

```dotenv
AUTH_ENABLED=true
AUTH_ISSUER=https://dev-wj6kifnw5uxt2gpk.us.auth0.com/
AUTH_AUDIENCE=IDENTIFIER_EXATO_DA_API
```

O proxy Vite usa Video Service em 8081 e Job Service em 8082. O login pode ser
verificado sem backend, mas as telas de vídeos mostrarão falha de conexão até
os serviços estarem disponíveis. Deploy não faz parte desta etapa.

## Nome do usuário

O perfil do Auth0 pode armazenar nome. Contudo, o formulário padrão de cadastro
por e-mail e senha não garante que um nome completo seja solicitado: `name` pode
ser um valor derivado do e-mail. Não interpretamos esse valor como nome completo.

A personalização de campos no **New Universal Login** usa recursos de customização
com requisitos de plano e domínio. Portanto, não foi incluído um campo local de
nome nem uma integração Management API, e não foi presumida a disponibilidade
desses recursos no plano grátis. Se o nome completo se tornar obrigatório,
precisaremos escolher um mecanismo compatível com o tenant. Isso não impede
login e cadastro com e-mail e senha.

## Testar

1. Sem sessão, abra `/videos`: deve aparecer a tela de entrada.
2. Use **Criar conta**: o Auth0 deve abrir seu formulário de cadastro por e-mail
   e senha. Crie uma conta e confira o retorno à rota solicitada.
3. Use **Sair**, depois **Entrar com e-mail e senha** com a conta criada.
4. Na página do Auth0, teste a opção de recuperação de senha e a entrega do e-mail.
5. Confira que Google não aparece entre as opções habilitadas para a SPA.
6. Com os serviços ativos, teste duas contas e confirme o isolamento de vídeos
   e jobs. Os recursos continuam vinculados ao `sub`, não ao nome ou e-mail.
7. Em caso de erro do callback, confira a tela de nova tentativa, sem detalhes
   técnicos do provedor expostos ao usuário.

## Referências

- [Database Connections](https://auth0.com/docs/authenticate/database-connections)
- [Parâmetros do SDK React](https://auth0.github.io/auth0-react/interfaces/AuthorizationParams.html)
- [Requisitos para nome no New Universal Login](https://support.auth0.com/center/s/article/Customize-Signup-Login-Partials-Prompts)

## Enviar o username cadastrado à SPA

`username` no perfil do tenant e `nickname` no ID token são campos distintos.
Para devolver o username real, crie uma Action **Login / Post Login** em
**Actions → Library → Create Action → Build from scratch**, usando o conteúdo de
`infrastructure/auth0/actions/add-username.js`. Clique em **Deploy**, depois
adicione a Action ao fluxo **Actions → Flows (ou Triggers) → Login / Post Login**
e clique em **Apply**. Não são necessários secrets nessa Action.

O frontend prioriza `https://video-insight-api/username` no cabeçalho e no perfil.
Esse endereço é um namespace de claim, não um endpoint. O vínculo dos vídeos
continua sendo `sub`. Saia e faça login novamente após aplicar a Action para
receber um ID token novo. Se o username não existir no perfil, não é inventado.
