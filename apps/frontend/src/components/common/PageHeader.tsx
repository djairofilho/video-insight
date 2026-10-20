import ChevronLeftRoundedIcon from '@mui/icons-material/ChevronLeftRounded'
import { Box, Link, Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'
import { Link as RouterLink } from 'react-router'
import { brand } from '../../app/theme'

interface PageHeaderProps {
  title: ReactNode
  /** Uma frase sobre os dados ou o objeto da tela, nunca sobre a interface. */
  description?: ReactNode
  actions?: ReactNode
  back?: { to: string; label: string }
}

export function PageHeader({ title, description, actions, back }: PageHeaderProps) {
  return (
    <Box component="header" sx={{ mb: { xs: 3, md: 4 } }}>
      {back && (
        <Link
          component={RouterLink}
          to={back.to}
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 0.25,
            mb: 1.5,
            ml: -0.5,
            fontSize: '0.875rem',
            fontWeight: 600,
            color: brand.muted,
            '&:hover': { color: brand.ink },
          }}
        >
          <ChevronLeftRoundedIcon fontSize="small" />
          {back.label}
        </Link>
      )}
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{ alignItems: { xs: 'flex-start', sm: 'center' }, justifyContent: 'space-between' }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h1" sx={{ overflowWrap: 'anywhere' }}>
            {title}
          </Typography>
          {description && (
            <Typography component="div" sx={{ color: brand.muted, mt: 0.75, maxWidth: '70ch' }}>
              {description}
            </Typography>
          )}
        </Box>
        {actions && (
          <Stack direction="row" spacing={1} sx={{ flexShrink: 0 }}>
            {actions}
          </Stack>
        )}
      </Stack>
    </Box>
  )
}
