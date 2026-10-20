import { Navigate, Outlet, useLocation } from 'react-router'
import { hasSession } from '../../services/authService'

/** Redireciona para `/login` sem sessão válida. Sem Auth0 configurado, todas as rotas ficam abertas. */
export function RequireAuth() {
  const location = useLocation()
  if (!hasSession()) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}
