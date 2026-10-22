import { act, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { SessionLoading } from './SessionLoading'
import { renderWithTheme } from '../test/render'

vi.mock('@auth0/auth0-react', () => ({ useAuth0: () => ({ loginWithRedirect: vi.fn() }) }))
afterEach(() => { vi.useRealTimers() })

it('troca o loading por uma nova tentativa de login após 15 segundos', () => {
  vi.useFakeTimers()
  const view = renderWithTheme(<SessionLoading />)
  expect(screen.queryByRole('button', { name: 'Entrar com e-mail e senha' })).not.toBeInTheDocument()
  act(() => { vi.advanceTimersByTime(15_000) })
  expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível restaurar sua sessão a tempo')
  expect(screen.getByRole('button', { name: 'Entrar com e-mail e senha' })).toBeEnabled()
  view.unmount()
  expect(vi.getTimerCount()).toBe(0)
})
