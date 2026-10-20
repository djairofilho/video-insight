import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest'
import { createHandlers } from '../mocks/handlers'
import { server } from './server'

// As rotas carregam sob demanda; a primeira transformação de cada tela pode passar de 1 s.
configure({ asyncUtilTimeout: 5000 })

// O jsdom não implementa mídia nem matchMedia.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }),
})
window.HTMLMediaElement.prototype.play = () => Promise.resolve()
window.HTMLMediaElement.prototype.pause = () => {}
window.scrollTo = () => {}
Element.prototype.scrollTo = () => {}
Element.prototype.scrollIntoView = () => {}

beforeAll(() => server.listen({ onUnhandledFrame: 'error' }))
beforeEach(() => server.resetHandlers(...createHandlers()))
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})
afterAll(() => server.close())
