import LockOutlinedIcon from '@mui/icons-material/LockOutlined'
import { Alert, Box, Button, Paper, Stack, Typography } from '@mui/material'
import { Logo } from '../components/layout/Logo'
import { Link as RouterLink, useLocation } from 'react-router'
import { isAuthEnabled } from '../services/authService'

/**
 * Tela de entrada. O fluxo OAuth2/PKCE com o Auth0 é conectado em `authService`; até lá, a aplicação funciona sem
 * login e esta tela apenas leva de volta aos vídeos.
 */
export function LoginPage() {
  const location = useLocation()
  const state = location.state as { from?: string; expired?: boolean } | null
  const destination = state?.from ?? '/videos'

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
            <Button variant="contained" size="large" startIcon={<LockOutlinedIcon />} disabled>
              Entrar com Auth0
            </Button>
          ) : (
            <>
              <Alert severity="info">A autenticação ainda não está configurada neste ambiente.</Alert>
              <Button component={RouterLink} to={destination} variant="contained" size="large">
                Continuar sem login
              </Button>
            </>
          )}
        </Stack>
      </Paper>
    </Box>
  )
}
