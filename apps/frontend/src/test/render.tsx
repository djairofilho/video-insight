import { CssBaseline, ThemeProvider } from '@mui/material'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { routes } from '../app/routes'
import { theme } from '../app/theme'

/** Renderiza a aplicação inteira numa rota, com as mesmas rotas de produção. */
export function renderRoute(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const view = render(
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <RouterProvider router={router} />
    </ThemeProvider>,
  )
  return { ...view, router }
}

export function renderWithTheme(element: ReactElement) {
  return render(<ThemeProvider theme={theme}>{element}</ThemeProvider>)
}
