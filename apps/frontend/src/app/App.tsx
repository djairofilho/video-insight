import { RouterProvider } from 'react-router'
import { setUnauthorizedHandler } from '../services/authService'
import { router } from './router'

setUnauthorizedHandler(() => {
  if (router.state.location.pathname !== '/login') {
    void router.navigate('/login', { state: { from: router.state.location.pathname, expired: true } })
  }
})

export function App() {
  return <RouterProvider router={router} />
}
