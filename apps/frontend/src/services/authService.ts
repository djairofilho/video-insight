/**
 * Ponto de integração com o Auth0 (etapa 3).
 *
 * O frontend não guarda tokens por conta própria: quem implementar o login registra aqui uma função que devolve o
 * access token atual (por exemplo, `getAccessTokenSilently` do SDK do Auth0) e o tratamento de sessão expirada. Sem
 * provedor configurado, as chamadas saem sem `Authorization` e as rotas ficam abertas.
 */
export type AccessTokenProvider = () => Promise<string | null>

export const authConfig = {
  domain: import.meta.env.VITE_AUTH0_DOMAIN ?? '',
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID ?? '',
  audience: import.meta.env.VITE_AUTH0_AUDIENCE ?? '',
}

export function isAuthEnabled(): boolean {
  return authConfig.domain !== ''
}

let tokenProvider: AccessTokenProvider = async () => null
let unauthorizedHandler: () => void = () => {}
let sessionChecker: () => boolean = () => true

/** Usado pelas rotas protegidas quando o Auth0 está configurado. */
export function setSessionChecker(checker: () => boolean): void {
  sessionChecker = checker
}

export function hasSession(): boolean {
  return !isAuthEnabled() || sessionChecker()
}

export function setAccessTokenProvider(provider: AccessTokenProvider): void {
  tokenProvider = provider
}

export function getAccessToken(): Promise<string | null> {
  return tokenProvider()
}

/** Chamado pelo cliente HTTP quando o Gateway responde 401. */
export function setUnauthorizedHandler(handler: () => void): void {
  unauthorizedHandler = handler
}

export function notifyUnauthorized(): void {
  unauthorizedHandler()
}
