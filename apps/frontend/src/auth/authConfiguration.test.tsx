import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { AuthProvider } from './AuthProvider'
import { authConfig, hasSession, setSessionChecker } from '../services/authService'
import { routes } from '../app/routes'
import { renderWithTheme } from '../test/render'

vi.mock('../app/router', () => ({ router: { navigate: vi.fn() } }))

describe('configuração ausente não libera autenticação', () => {
  beforeEach(() => {
    authConfig.domain = ''
    authConfig.clientId = ''
    authConfig.audience = ''
    setSessionChecker(() => false)
  })

  it('não considera ausência de configuração uma sessão válida', () => {
    expect(hasSession()).toBe(false)
  })

  it.each(['/videos', '/videos/new', '/jobs/123/result'])(
    'protege acesso direto a %s sem provedor configurado', async (path) => {
      const router = createMemoryRouter(routes, { initialEntries: [path] })
      renderWithTheme(<AuthProvider><RouterProvider router={router} /></AuthProvider>)
      await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
      expect(await screen.findByRole('alert')).toHaveTextContent('Autenticação não configurada')
      expect(router.state.location.state).toEqual({ from: path })
      expect(screen.queryByRole('button', { name: 'Continuar sem login' })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Entrar com e-mail e senha' })).not.toBeInTheDocument()
    },
  )
})
