/// <reference types="vitest/config" />
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig, loadEnv } from 'vite'

// No modo `mock` (npm run dev:mock) o Gateway é simulado no navegador pelo MSW, sem depender de arquivo .env.
const mockEnv = {
  'import.meta.env.VITE_USE_MOCKS': JSON.stringify('true'),
  'import.meta.env.VITE_API_BASE_URL': JSON.stringify('http://gateway.test/api/v1'),
}

// No modo `services` (npm run dev:local) o servidor do Vite faz o papel do Gateway: encaminha cada rota ao serviço
// rodando na máquina, como o krakend.json faz na AWS. Assim o navegador fala com uma única origem e não depende de CORS.
const localGateway = {
  '^/api/v1/videos/[^/]+/jobs': 'http://localhost:8082',
  '/api/v1/jobs': 'http://localhost:8082',
  '/api/v1/videos': 'http://localhost:8081',
}

// https://vite.dev/config/
export default defineConfig(({ mode, command }) => {
  if (command === 'build' && mode === 'production') {
    const env = { ...loadEnv(mode, process.cwd(), ''), ...process.env }
    for (const key of ['VITE_AUTH0_DOMAIN', 'VITE_AUTH0_CLIENT_ID', 'VITE_AUTH0_AUDIENCE']) {
      if (!env[key]?.trim()) throw new Error(`${key} é obrigatório no build de produção`)
    }
    if (!env.VITE_API_BASE_URL?.startsWith('https://')) {
      throw new Error('VITE_API_BASE_URL precisa usar HTTPS em produção')
    }
    if (env.VITE_USE_MOCKS === 'true') throw new Error('Mocks não podem ser publicados em produção')
  }
  return ({
  define:
    mode === 'mock'
      ? mockEnv
      : mode === 'services'
        ? { 'import.meta.env.VITE_API_BASE_URL': JSON.stringify('/api/v1') }
        : {},
  server: mode === 'services' ? { proxy: localGateway } : undefined,
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    env: { VITE_API_BASE_URL: 'http://gateway.test/api/v1' },
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/main.tsx', 'src/mocks/browser.ts', 'src/test/**', 'src/**/*.test.{ts,tsx}'],
    },
  },
})
})
