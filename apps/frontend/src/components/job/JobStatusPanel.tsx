import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import RadioButtonUncheckedRoundedIcon from '@mui/icons-material/RadioButtonUncheckedRounded'
import { Box, CircularProgress, LinearProgress, Stack, Typography } from '@mui/material'
import type { Job } from '../../types/job'
import { stagesFor } from '../../utils/jobs'
import { JOB_STAGE_LABELS } from '../../utils/labels'

export function JobProgress({ job }: { job: Job }) {
  const stages = stagesFor(job)
  const current = job.stage ? stages.indexOf(job.stage) : -1
  const progress = Math.min(100, Math.max(0, job.progress_percent))

  return (
    <Stack spacing={3}>
      <Box>
        <Stack direction="row" sx={{ justifyContent: 'space-between', mb: 1 }}>
          <Typography sx={{ fontWeight: 600 }}>
            {job.status === 'queued' ? 'Aguardando na fila' : job.stage ? JOB_STAGE_LABELS[job.stage] : 'Iniciando'}
          </Typography>
          {job.status === 'processing' && (
            <Typography sx={{ color: 'text.secondary' }} aria-hidden>
              {progress}%
            </Typography>
          )}
        </Stack>
        <LinearProgress
          variant={job.status === 'queued' ? 'indeterminate' : 'determinate'}
          value={progress}
          aria-label="Progresso estimado do processamento"
          aria-valuetext={job.status === 'queued' ? 'Na fila' : `${progress}%`}
        />
        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 1 }}>
          O percentual é uma estimativa por etapa, não uma previsão de tempo.
        </Typography>
      </Box>
      <Stack component="ol" spacing={1} sx={{ listStyle: 'none', p: 0, m: 0 }} aria-label="Etapas do processamento">
        {stages.map((stage, index) => {
          const done = current > index
          const active = current === index && job.status === 'processing'
          return (
            <Stack
              component="li"
              key={stage}
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
              <Typography sx={{ fontWeight: active ? 600 : 400 }}>{JOB_STAGE_LABELS[stage]}</Typography>
            </Stack>
          )
        })}
      </Stack>
    </Stack>
  )
}
