import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import { Alert, AlertTitle, Box, Button, CircularProgress, Paper, Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'
import { correlationIdOf, describeError } from '../../utils/errorMessages'

export function LoadingState({ label = 'Carregando…' }: { label?: string }) {
  return (
    <Stack role="status" spacing={2} sx={{ alignItems: 'center', py: 8, color: 'text.secondary' }}>
      <CircularProgress size={28} color="secondary" />
      <Typography>{label}</Typography>
    </Stack>
  )
}

interface ErrorStateProps {
  error: unknown
  title?: string
  onRetry?: () => void
  retryLabel?: string
}

/** Erro com ação explícita de nova tentativa e o identificador da requisição para suporte. */
export function ErrorState({ error, title = 'Não foi possível carregar', onRetry, retryLabel = 'Tentar novamente' }: ErrorStateProps) {
  const correlationId = correlationIdOf(error)
  return (
    <Alert
      severity="error"
      variant="outlined"
      action={
        onRetry && (
          <Button color="inherit" size="small" startIcon={<RefreshRoundedIcon />} onClick={onRetry}>
            {retryLabel}
          </Button>
        )
      }
      sx={{ alignItems: 'center' }}
    >
      <AlertTitle>{title}</AlertTitle>
      {describeError(error)}
      {correlationId && (
        <Typography variant="caption" component="p" sx={{ mt: 0.5, opacity: 0.8 }}>
          Código da requisição: {correlationId}
        </Typography>
      )}
    </Alert>
  )
}

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: ReactNode
  action?: ReactNode
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <Paper
      variant="outlined"
      sx={{ py: { xs: 6, md: 9 }, px: 3, textAlign: 'center', borderStyle: 'dashed', borderWidth: 2, borderColor: 'divider', bgcolor: 'background.paper' }}
    >
      {icon && <Box sx={{ color: 'secondary.main', mb: 2, '& svg': { fontSize: 40 } }}>{icon}</Box>}
      <Typography variant="h2">
        {title}
      </Typography>
      {description && (
        <Typography sx={{ color: 'text.secondary', mt: 1, mx: 'auto', maxWidth: '48ch' }}>{description}</Typography>
      )}
      {action && <Box sx={{ mt: 3 }}>{action}</Box>}
    </Paper>
  )
}
