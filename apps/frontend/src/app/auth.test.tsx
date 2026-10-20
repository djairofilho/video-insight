import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderRoute } from '../test/render'

// Simula o Auth0 configurado e sem sessão.
vi.mock('../services/authService', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../services/authService')>()),
  isAuthEnabled: () => true,
  hasSession: () => false,
}))

describe('rotas protegidas', () => {
  it('redireciona para o login sem sessão válida', async () => {
    const { router } = renderRoute('/videos')
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(await screen.findByRole('heading', { name: 'Entre para ver seus vídeos' })).toBeInTheDocument()
    expect(router.state.location.state).toEqual({ from: '/videos' })
  })
})
