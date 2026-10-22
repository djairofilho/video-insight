import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { AuthProvider } from './AuthProvider'
import { getAccessToken, hasSession } from '../services/authService'
import { safeReturnTo } from './returnTo'

const state = vi.hoisted(() => ({
  error: undefined as Error | undefined,
  loginWithRedirect: vi.fn(),
  isLoading: false,
  isAuthenticated: true,
  getAccessTokenSilently: vi.fn().mockResolvedValue('access-token'),
  navigate: vi.fn(),
  callback: undefined as undefined | ((state: { returnTo: string }) => void),
}))
vi.mock('../app/router', () => ({ router: { navigate: state.navigate } }))
vi.mock('@auth0/auth0-react', () => ({
  Auth0Provider: ({ children, onRedirectCallback }: { children: ReactNode; onRedirectCallback: typeof state.callback }) => {
    state.callback = onRedirectCallback
    return children
  },
  useAuth0: () => state,
}))
vi.mock('../services/authService', async (original) => ({
  ...(await original<typeof import('../services/authService')>()),
  isAuthEnabled: () => true,
  authConfig: { domain: 'example.auth0.com', clientId: 'public-client', audience: 'api' },
}))

describe('sessão Auth0', () => {
  beforeEach(() => { state.isLoading = false; state.isAuthenticated = true; state.error = undefined; vi.clearAllMocks() })

  it('aguarda o SDK antes de montar as rotas', () => {
    state.isLoading = true
    render(<AuthProvider><p>Rotas protegidas</p></AuthProvider>)
    expect(screen.queryByText('Rotas protegidas')).not.toBeInTheDocument()
  })

  it('conecta o access token e a sessão ao cliente HTTP', async () => {
    render(<AuthProvider><p>Rotas protegidas</p></AuthProvider>)
    await waitFor(() => expect(hasSession()).toBe(true))
    expect(await getAccessToken()).toBe('access-token')
  })

  it('restaura a rota sem recarregar e perder o token em memória', () => {
    render(<AuthProvider><p>Rotas protegidas</p></AuthProvider>)
    state.callback?.({ returnTo: '/videos/123' })
    expect(state.navigate).toHaveBeenCalledWith('/videos/123', { replace: true })
  })

  it('oferece nova tentativa quando o callback falha', () => {
    state.error = new Error('private provider details')
    render(<AuthProvider><p>Rotas protegidas</p></AuthProvider>)
    expect(screen.getByRole('heading', { name: 'Vamos tentar entrar novamente' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Entrar com e-mail e senha' })).toBeInTheDocument()
    expect(screen.queryByText('Rotas protegidas')).not.toBeInTheDocument()
    expect(screen.queryByText('private provider details')).not.toBeInTheDocument()
  })

  it('rejeita destinos externos no retorno do login', () => {
    for (const value of ['https://evil.example', '//evil.example', '/\\evil.example']) {
      expect(safeReturnTo(value)).toBe('/videos')
    }
  })
})
