import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import RadioButtonUncheckedRoundedIcon from '@mui/icons-material/RadioButtonUncheckedRounded'
import { Box, CircularProgress, LinearProgress, Stack, Typography } from '@mui/material'
import type { UploadPhase } from '../../hooks/useVideoUpload'

const STEPS: { phase: UploadPhase; label: string }[] = [
  { phase: 'validating', label: 'Verificando o arquivo' },
  { phase: 'creating', label: 'Cadastrando o vídeo' },
  { phase: 'uploading', label: 'Enviando para o armazenamento' },
  { phase: 'confirming', label: 'Confirmando o envio' },
]

const ORDER: UploadPhase[] = ['validating', 'creating', 'uploading', 'confirming', 'done']

interface UploadProgressProps {
  phase: UploadPhase
  progress: number
}

export function UploadProgress({ phase, progress }: UploadProgressProps) {
  const currentIndex = ORDER.indexOf(phase)
  return (
    <Stack spacing={2}>
      <Stack component="ol" spacing={1.25} sx={{ listStyle: 'none', p: 0, m: 0 }}>
        {STEPS.map((step, index) => {
          const done = currentIndex > index
          const active = currentIndex === index
          return (
            <Stack
              component="li"
              key={step.phase}
              direction="row"
              spacing={1.5}
              sx={{ alignItems: 'center', color: done || active ? 'text.primary' : 'text.secondary' }}
              aria-current={active ? 'step' : undefined}
            >
              <Box sx={{ width: 22, display: 'grid', placeItems: 'center' }}>
                {done ? (
                  <CheckCircleRoundedIcon fontSize="small" color="success" />
                ) : active ? (
                  <CircularProgress size={16} aria-hidden />
                ) : (
                  <RadioButtonUncheckedRoundedIcon fontSize="small" />
                )}
              </Box>
              <Typography sx={{ fontWeight: active ? 600 : 400 }}>{step.label}</Typography>
              {step.phase === 'uploading' && active && (
                <Typography sx={{ color: 'text.secondary', ml: 'auto !important' }}>{progress}%</Typography>
              )}
            </Stack>
          )
        })}
      </Stack>
      {phase === 'uploading' && (
        <LinearProgress variant="determinate" value={progress} aria-label="Progresso do envio" />
      )}
    </Stack>
  )
}
