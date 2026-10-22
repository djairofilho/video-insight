import { Auth0Provider, useAuth0, type AppState } from '@auth0/auth0-react'
import { useLayoutEffect, type ReactNode } from 'react'
import { SessionLoading } from './SessionLoading'
import { router } from '../app/router'
import { AuthErrorPage } from './AuthErrorPage'
import { SessionContext } from './session'
import { safeReturnTo } from './returnTo'
import { authConfig, isAuthEnabled, setAccessTokenProvider, setSessionChecker } from '../services/authService'

function SessionBridge({ children }: { children: ReactNode }) {
  const { isLoading, isAuthenticated, getAccessTokenSilently, error } = useAuth0()
  useLayoutEffect(() => {
    setAccessTokenProvider(async () => (await getAccessTokenSilently()) ?? null)
    setSessionChecker(() => isAuthenticated)
    return () => {
      setAccessTokenProvider(async () => null)
      setSessionChecker(() => false)
    }
  }, [getAccessTokenSilently, isAuthenticated])
  if (error) return <AuthErrorPage />
  if (isLoading) return <SessionLoading />
  return <SessionContext.Provider value={isAuthenticated}>{children}</SessionContext.Provider>
}

export function AuthProvider({ children }: { children: ReactNode }) {
  if (!isAuthEnabled()) return <SessionContext.Provider value={false}>{children}</SessionContext.Provider>
  return (
    <Auth0Provider domain={authConfig.domain} clientId={authConfig.clientId}
      authorizationParams={{ redirect_uri: window.location.origin, audience: authConfig.audience, scope: 'openid profile email' }}
      cacheLocation="memory"
      authorizeTimeoutInSeconds={10}
      httpTimeoutInSeconds={10}
      onRedirectCallback={(state?: AppState) => { void router.navigate(safeReturnTo(state?.returnTo), { replace: true }) }}>
      <SessionBridge>{children}</SessionBridge>
    </Auth0Provider>
  )
}
