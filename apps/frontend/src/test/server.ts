import { setupServer } from 'msw/node'

/** Gateway simulado nos testes; `setup.ts` recria os handlers (e o estado em memória) antes de cada teste. */
export const server = setupServer()
