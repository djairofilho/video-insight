import '@fontsource-variable/figtree'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import './index.css'

async function enableMocks() {
  if (import.meta.env.VITE_USE_MOCKS === 'true') {
    const { startMockWorker } = await import('./mocks/browser')
    await startMockWorker()
  }
}

void enableMocks().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
