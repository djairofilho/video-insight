/** Integração do SDK Auth0 com o cliente HTTP e as rotas protegidas. */
export type AccessTokenProvider = () => Promise<string | null>

export const authConfig = {
  domain: import.meta.env.VITE_AUTH0_DOMAIN ?? '',
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID ?? '',
  audience: import.meta.env.VITE_AUTH0_AUDIENCE ?? '',
}

export function isAuthEnabled(): boolean {
  return Boolean(authConfig.domain.trim() && authConfig.clientId.trim() && authConfig.audience.trim())
}

let tokenProvider: AccessTokenProvider = async () => null
let unauthorizedHandler: () => void = () => {}
let sessionChecker: () => boolean = () => false

/** Usado pelas rotas protegidas quando o Auth0 está configurado. */
export function setSessionChecker(checker: () => boolean): void {
  sessionChecker = checker
}

export function hasSession(): boolean {
  return sessionChecker()
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
