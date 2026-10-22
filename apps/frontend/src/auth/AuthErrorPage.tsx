import { Alert, Box, Paper, Stack, Typography } from '@mui/material'
import { Logo } from '../components/layout/Logo'
import { AuthLoginButton } from './AuthLoginButton'

/** Erros do callback também permitem reiniciar o login, sem expor dados do provedor. */
export function AuthErrorPage({ message = 'O login não foi concluído. Tente novamente com seu e-mail e senha.' }: { message?: string }) {
  return (
    <Box sx={{ minHeight: '100svh', display: 'grid', placeItems: 'center', p: 2 }}>
      <Paper variant="outlined" sx={{ p: { xs: 3, md: 5 }, maxWidth: 440, width: '100%' }}>
        <Stack spacing={3}>
          <Logo />
          <Typography variant="h1">Vamos tentar entrar novamente</Typography>
          <Alert severity="error">{message}</Alert>
          <AuthLoginButton returnTo={window.location.pathname} />
        </Stack>
      </Paper>
    </Box>
  )
}
