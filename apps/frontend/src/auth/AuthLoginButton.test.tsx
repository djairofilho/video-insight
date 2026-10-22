import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthLoginButton } from './AuthLoginButton'
import { renderWithTheme } from '../test/render'

const { loginWithRedirect } = vi.hoisted(() => ({ loginWithRedirect: vi.fn() }))
vi.mock('@auth0/auth0-react', () => ({ useAuth0: () => ({ loginWithRedirect }) }))

describe('entrada e cadastro no Auth0', () => {
  beforeEach(() => { loginWithRedirect.mockReset() })

  it('usa a conexão de e-mail e senha e preserva a rota solicitada', async () => {
    loginWithRedirect.mockReturnValue(new Promise(() => {}))
    renderWithTheme(<AuthLoginButton returnTo="/videos/123" />)
    fireEvent.click(screen.getByRole('button', { name: 'Entrar com e-mail e senha' }))
    await waitFor(() => expect(loginWithRedirect).toHaveBeenCalledWith({
      appState: { returnTo: '/videos/123' }, authorizationParams: { connection: 'Username-Password-Authentication' },
    }))
    expect(screen.getByRole('button', { name: 'Redirecionando…' })).toBeDisabled()
  })

  it('abre o cadastro hospedado no Auth0 sem coletar credenciais localmente', () => {
    loginWithRedirect.mockReturnValue(new Promise(() => {}))
    renderWithTheme(<AuthLoginButton returnTo="/videos/new" signup />)
    fireEvent.click(screen.getByRole('button', { name: 'Criar conta' }))
    expect(loginWithRedirect).toHaveBeenCalledWith({
      appState: { returnTo: '/videos/new' },
      authorizationParams: { connection: 'Username-Password-Authentication', screen_hint: 'signup' },
    })
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('permite tentar novamente quando o redirecionamento falha', async () => {
    loginWithRedirect.mockRejectedValueOnce(new Error('sensitive provider details'))
    renderWithTheme(<AuthLoginButton returnTo="//external.example" />)
    fireEvent.click(screen.getByRole('button', { name: 'Entrar com e-mail e senha' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível iniciar a autenticação')
    expect(screen.getByRole('button', { name: 'Entrar com e-mail e senha' })).toBeEnabled()
    expect(screen.queryByText('sensitive provider details')).not.toBeInTheDocument()
    expect(loginWithRedirect).toHaveBeenCalledWith(expect.objectContaining({ appState: { returnTo: '/videos' } }))
    loginWithRedirect.mockReturnValue(new Promise(() => {}))
    fireEvent.click(screen.getByRole('button', { name: 'Entrar com e-mail e senha' }))
    expect(loginWithRedirect).toHaveBeenCalledTimes(2)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
