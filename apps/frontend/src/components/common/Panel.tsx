import { Box, Paper, Stack, Typography, type SxProps, type Theme } from '@mui/material'
import type { ReactNode } from 'react'
import { brand } from '../../app/theme'

interface PanelProps {
  title?: ReactNode
  titleId?: string
  /** Faixa de 4px no topo: azul para conteúdo gerado, turquesa para o que está pronto. */
  accent?: 'blue' | 'teal'
  actions?: ReactNode
  component?: 'section' | 'div' | 'nav' | 'aside'
  children: ReactNode
  sx?: SxProps<Theme>
}

const ACCENTS = { blue: brand.blue, teal: brand.teal }

/** Superfície padrão do app: branca, borda leve, raio 16 e título em frase normal. */
export function Panel({ title, titleId, accent, actions, component = 'section', children, sx }: PanelProps) {
  return (
    <Paper
      component={component}
      variant="outlined"
      aria-labelledby={title ? titleId : undefined}
      sx={[
        { p: { xs: 2, md: 2.5 }, overflow: 'hidden', position: 'relative' },
        accent ? { borderTop: `4px solid ${ACCENTS[accent]}` } : {},
        ...(Array.isArray(sx) ? sx : [sx]),
      ]}
    >
      {(title || actions) && (
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center', justifyContent: 'space-between', mb: 1.5, minHeight: 30 }}>
          {title && (
            <Typography id={titleId} component="h2" sx={{ fontSize: '1.125rem', fontWeight: 700, letterSpacing: '-0.01em', lineHeight: 1.35 }}>
              {title}
            </Typography>
          )}
          {actions && <Box sx={{ flexShrink: 0 }}>{actions}</Box>}
        </Stack>
      )}
      {children}
    </Paper>
  )
}
