import { useContext } from 'react'
import { SessionContext } from '../../auth/session'
import { Navigate, Outlet, useLocation } from 'react-router'
import { hasSession } from '../../services/authService'

/** Redireciona para `/login` sem sessão válida. Configuração ausente nunca concede acesso. */
export function RequireAuth() {
  const location = useLocation()
  const authenticated = useContext(SessionContext)
  if (!(authenticated ?? hasSession())) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}
