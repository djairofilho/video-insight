import { setupWorker } from 'msw/browser'
import { createHandlers } from './handlers'

/** Liga o Gateway simulado no navegador. Ativado com `VITE_USE_MOCKS=true`; nunca entra no fluxo normal. */
export function startMockWorker() {
  const worker = setupWorker(...createHandlers(import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')))
  return worker.start({ onUnhandledFrame: 'bypass', quiet: true })
}
