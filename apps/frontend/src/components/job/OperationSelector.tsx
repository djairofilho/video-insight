import { Box, Checkbox, Stack, Typography } from '@mui/material'
import { brand } from '../../app/theme'
import type { Operation } from '../../types/job'
import { OPERATION_LABELS, OPERATION_ORDER } from '../../utils/labels'

const DESCRIPTIONS: Record<Operation, string> = {
  transcription: 'Texto completo com timestamps, para exportar em TXT, SRT ou JSON.',
  summary: 'Os pontos principais do vídeo em poucos parágrafos.',
  chapters: 'O vídeo dividido em partes, com explicações e diagramas.',
}

interface OperationSelectorProps {
  value: Operation[]
  onChange: (operations: Operation[]) => void
  disabled?: boolean
}

export function OperationSelector({ value, onChange, disabled = false }: OperationSelectorProps) {
  const toggle = (operation: Operation) => {
    const next = value.includes(operation) ? value.filter((item) => item !== operation) : [...value, operation]
    onChange(OPERATION_ORDER.filter((item) => next.includes(item)))
  }

  return (
    <Box component="fieldset" sx={{ border: 0, p: 0, m: 0 }}>
      <Box component="legend" sx={{ mb: 1.25, fontWeight: 600, color: brand.ink }}>
        O que você quer gerar?
      </Box>
      <Stack spacing={1}>
        {OPERATION_ORDER.map((operation) => {
          const checked = value.includes(operation)
          const inputId = `operation-${operation}`
          return (
            <Box
              key={operation}
              component="label"
              htmlFor={inputId}
              sx={{
                display: 'flex',
                gap: 1,
                alignItems: 'flex-start',
                px: 1.5,
                py: 1.25,
                borderRadius: '12px',
                border: `1px solid ${checked ? '#9cc2ff' : brand.border}`,
                bgcolor: checked ? brand.blueTint : brand.surface,
                cursor: disabled ? 'default' : 'pointer',
                transition: 'border-color 150ms, background-color 150ms',
                '&:hover': disabled ? undefined : { borderColor: checked ? '#6fa6ff' : brand.control },
              }}
            >
              <Checkbox id={inputId} checked={checked} disabled={disabled} onChange={() => toggle(operation)} sx={{ m: -0.75, mt: -0.5 }} />
              <Box sx={{ minWidth: 0 }}>
                <Typography sx={{ fontWeight: 650, color: brand.ink, lineHeight: 1.4 }}>{OPERATION_LABELS[operation]}</Typography>
                <Typography variant="body2" sx={{ color: brand.muted }}>
                  {DESCRIPTIONS[operation]}
                </Typography>
              </Box>
            </Box>
          )
        })}
      </Stack>
    </Box>
  )
}
