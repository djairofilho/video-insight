import '@fontsource-variable/figtree'
import { StrictMode } from 'react'
import { CssBaseline, ThemeProvider } from '@mui/material'
import { theme } from './app/theme'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import './index.css'
import { AuthProvider } from './auth/AuthProvider'

async function enableMocks() {
  if (import.meta.env.VITE_USE_MOCKS === 'true') {
    const { startMockWorker } = await import('./mocks/browser')
    await startMockWorker()
  }
}

void enableMocks().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <ThemeProvider theme={theme}>
        <CssBaseline enableColorScheme />
        <AuthProvider><App /></AuthProvider>
      </ThemeProvider>
    </StrictMode>,
  )
})
