import { CssBaseline, ThemeProvider } from '@mui/material'
import { createBrowserRouter, RouterProvider } from 'react-router'
import { setUnauthorizedHandler } from '../services/authService'
import { routes } from './routes'
import { theme } from './theme'

const router = createBrowserRouter(routes)

setUnauthorizedHandler(() => {
  if (router.state.location.pathname !== '/login') {
    void router.navigate('/login', { state: { from: router.state.location.pathname, expired: true } })
  }
})

export function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline enableColorScheme />
      <RouterProvider router={router} />
    </ThemeProvider>
  )
}
