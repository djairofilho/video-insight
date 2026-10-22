import { safeReturnTo } from '../auth/returnTo'
import { AuthLoginButton } from '../auth/AuthLoginButton'
import { Alert, Box, Paper, Stack, Typography } from '@mui/material'
import { Logo } from '../components/layout/Logo'
import { useLocation } from 'react-router'
import { isAuthEnabled } from '../services/authService'

export function LoginPage() {
  const location = useLocation()
  const state = location.state as { from?: string; expired?: boolean } | null
  const destination = safeReturnTo(state?.from)

  return (
    <Box sx={{ minHeight: '100svh', display: 'grid', placeItems: 'center', p: 2 }}>
      <Paper variant="outlined" sx={{ p: { xs: 3, md: 5 }, maxWidth: 440, width: '100%', borderTop: '4px solid #0a66ff' }}>
        <Stack spacing={3}>
          <Logo />
          <Box>
            <Typography variant="h1">
              Entre para ver seus vídeos
            </Typography>
            <Typography sx={{ color: 'text.secondary', mt: 1 }}>
              Transcrição, resumo e capítulos automáticos para aulas, reuniões e entrevistas.
            </Typography>
          </Box>
          {state?.expired && <Alert severity="warning">Sua sessão expirou. Entre novamente.</Alert>}
          {isAuthEnabled() ? (
            <Stack spacing={2}>
              <AuthLoginButton returnTo={destination} />
              <AuthLoginButton returnTo={destination} signup />
              <Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center' }}>
                Crie sua conta ou entre com e-mail e senha. O cadastro e a recuperação de senha são feitos na página segura de autenticação.
              </Typography>
            </Stack>
          ) : (
            <Alert severity="error">
              Autenticação não configurada. Preencha VITE_AUTH0_DOMAIN, VITE_AUTH0_CLIENT_ID e VITE_AUTH0_AUDIENCE no arquivo .env.local e reinicie o frontend.
            </Alert>
          )}
        </Stack>
      </Paper>
    </Box>
  )
}
