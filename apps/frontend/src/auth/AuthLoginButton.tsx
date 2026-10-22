import { useAuth0 } from '@auth0/auth0-react'
import LockOutlinedIcon from '@mui/icons-material/LockOutlined'
import { Alert, Button, CircularProgress } from '@mui/material'
import { useState } from 'react'
import { safeReturnTo } from './returnTo'

/** Credenciais e cadastro são tratados exclusivamente pelo Universal Login do Auth0. */
export function AuthLoginButton({ returnTo, signup = false }: { returnTo?: string; signup?: boolean }) {
  const { loginWithRedirect } = useAuth0()
  const [pending, setPending] = useState(false)
  const [failed, setFailed] = useState(false)

  async function login() {
    setPending(true)
    setFailed(false)
    try {
      await loginWithRedirect({
        appState: { returnTo: safeReturnTo(returnTo) },
        authorizationParams: { connection: 'Username-Password-Authentication', ...(signup ? { screen_hint: 'signup' } : {}) },
      })
    } catch {
      setFailed(true)
      setPending(false)
    }
  }

  return (
    <>
      {failed && <Alert severity="error">Não foi possível iniciar a autenticação. Tente novamente.</Alert>}
      <Button variant={signup ? 'outlined' : 'contained'} size="large" fullWidth disabled={pending} onClick={() => void login()}
        startIcon={pending ? <CircularProgress size={18} color="inherit" /> : <LockOutlinedIcon />}>
        {pending ? 'Redirecionando…' : signup ? 'Criar conta' : 'Entrar com e-mail e senha'}
      </Button>
    </>
  )
}
