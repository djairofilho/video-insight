import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded'
import ReplayRoundedIcon from '@mui/icons-material/ReplayRounded'
import { Alert, AlertTitle, Box, Button, Link, Stack, Typography } from '@mui/material'
import { brand } from '../app/theme'
import { useState } from 'react'
import { Link as RouterLink, useParams } from 'react-router'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { PageHeader } from '../components/common/PageHeader'
import { Panel } from '../components/common/Panel'
import { ErrorState, LoadingState } from '../components/common/States'
import { JobStatusChip } from '../components/common/StatusChip'
import { JobProgress } from '../components/job/JobStatusPanel'
import { VideoThumbnail } from '../components/video/VideoThumbnail'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { useJobPolling } from '../hooks/useJobPolling'
import { cancelJob, retryJob } from '../services/jobService'
import { getVideo } from '../services/videoService'
import type { Job } from '../types/job'
import { describeError, isNotFound } from '../utils/errorMessages'
import { formatBytes } from '../utils/formatBytes'
import { formatDateTime, formatDuration } from '../utils/formatDuration'
import { OPERATION_LABELS } from '../utils/labels'

export function JobPage() {
  const { jobId = '' } = useParams()
  const { job, error, restart } = useJobPolling(jobId)

  if (!job && error !== undefined) {
    return (
      <>
        <PageHeader title="Processamento" back={{ to: '/videos', label: 'Meus vídeos' }} />
        <ErrorState
          error={error}
          title={isNotFound(error) ? 'Processamento não encontrado' : 'Não foi possível carregar o processamento'}
          onRetry={isNotFound(error) ? undefined : () => window.location.reload()}
        />
      </>
    )
  }
  if (!job) {
    return <LoadingState label="Carregando o processamento…" />
  }
  return <JobDetails job={job} pollingError={error} onChange={restart} />
}

interface JobDetailsProps {
  job: Job
  pollingError?: unknown
  onChange: (job: Job) => void
}

function JobDetails({ job, pollingError, onChange }: JobDetailsProps) {
  const [confirmingCancel, setConfirmingCancel] = useState(false)
  const [busy, setBusy] = useState<'cancel' | 'retry' | null>(null)
  const [actionError, setActionError] = useState<unknown>(null)
  const active = job.status === 'queued' || job.status === 'processing'

  const run = async (action: 'cancel' | 'retry') => {
    setBusy(action)
    setActionError(null)
    try {
      onChange(action === 'cancel' ? await cancelJob(job.id) : await retryJob(job.id))
      setConfirmingCancel(false)
    } catch (failure) {
      setActionError(failure)
    } finally {
      setBusy(null)
    }
  }

  return (
    <>
      <PageHeader
        title={job.operations.map((operation) => OPERATION_LABELS[operation]).join(' · ')}
        description={[`criado em ${formatDateTime(job.created_at)}`, job.attempt > 1 ? `Tentativa ${job.attempt}` : null].filter(Boolean).join(' · ')}
        back={{ to: `/videos/${job.video_id}`, label: 'Voltar ao vídeo' }}
        actions={
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <JobStatusChip status={job.status} />
          </Box>
        }
      />

      <Box sx={{ display: 'grid', gap: 3, gridTemplateColumns: { xs: '1fr', md: '7fr 5fr' }, alignItems: 'start' }}>
      <Box sx={{ minWidth: 0 }}>
      <Panel accent={job.status === 'completed' ? 'teal' : job.status === 'failed' || job.status === 'cancelled' ? undefined : 'blue'} sx={{ p: { xs: 2.5, md: 3 } }}>
        <Box aria-live="polite">
        {active && <JobProgress job={job} />}

        {job.status === 'completed' && (
          <Stack spacing={2} sx={{ alignItems: 'flex-start' }}>
            <Typography variant="h2">
              Pronto! O resultado está disponível.
            </Typography>
            <Button
              component={RouterLink}
              to={`/jobs/${job.id}/result`}
              variant="contained"
              size="large"
              endIcon={<ArrowForwardRoundedIcon />}
            >
              Ver resultado
            </Button>
          </Stack>
        )}

        {job.status === 'failed' && (
          <Alert
            severity="error"
            variant="outlined"
            action={
              job.error?.retryable !== false && (
                <Button
                  color="inherit"
                  size="small"
                  variant="outlined"
                  startIcon={<ReplayRoundedIcon />}
                  loading={busy === 'retry'}
                  onClick={() => void run('retry')}
                >
                  Tentar novamente
                </Button>
              )
            }
          >
            <AlertTitle>O processamento falhou</AlertTitle>
            {job.error?.message ?? 'Ocorreu um erro durante o processamento.'}
            {job.error?.retryable === false && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                Essa falha não se resolve com uma nova tentativa. Verifique o arquivo e envie o vídeo novamente.
              </Typography>
            )}
            {job.error && (
              <Typography variant="caption" component="p" sx={{ mt: 0.5, opacity: 0.8 }}>
                Código: {job.error.code}
              </Typography>
            )}
          </Alert>
        )}

        {job.status === 'cancelled' && (
          <Alert severity="info" variant="outlined">
            <AlertTitle>Processamento cancelado</AlertTitle>
            Para gerar os resultados, volte ao vídeo e inicie um novo processamento.
          </Alert>
        )}

        {actionError !== null && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {describeError(actionError)}
          </Alert>
        )}
        {pollingError !== undefined && active && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            Perdemos a conexão por um instante. Continuamos tentando atualizar o andamento…
          </Alert>
        )}
        </Box>
      </Panel>

      {active && (
        <Box sx={{ mt: 2 }}>
          <Button color="inherit" onClick={() => setConfirmingCancel(true)} sx={{ color: 'text.secondary' }}>
            Cancelar processamento
          </Button>
        </Box>
      )}

      </Box>
      <JobVideoCard videoId={job.video_id} />
      </Box>

      <ConfirmDialog
        open={confirmingCancel}
        title="Cancelar o processamento?"
        description="O trabalho em andamento será descartado. Você poderá iniciar um novo processamento depois."
        confirmLabel="Cancelar processamento"
        destructive
        busy={busy === 'cancel'}
        onConfirm={() => void run('cancel')}
        onClose={() => setConfirmingCancel(false)}
      />
    </>
  )
}

/** Contexto do processamento: de qual vídeo ele é, com a miniatura e o caminho de volta. */
function JobVideoCard({ videoId }: { videoId: string }) {
  const video = useAsyncResource(`job-video:${videoId}`, (signal) => getVideo(videoId, signal))
  if (video.state.status !== 'success') {
    return (
      <Panel title="Vídeo" titleId="job-video-title">
        <Typography variant="body2" role="status" sx={{ color: brand.muted }}>
          {video.state.status === 'loading' ? 'Carregando o vídeo…' : 'Não foi possível carregar os dados do vídeo.'}
        </Typography>
      </Panel>
    )
  }
  const data = video.state.data
  return (
    <Panel title="Vídeo" titleId="job-video-title">
      <VideoThumbnail video={data} width="100%" />
      <Typography sx={{ fontWeight: 650, color: brand.ink, mt: 1.5, overflowWrap: 'anywhere' }}>{data.file_name}</Typography>
      <Typography variant="body2" sx={{ color: brand.muted }}>
        {formatDuration(data.duration_seconds)} · {formatBytes(data.size_bytes)}
      </Typography>
      <Link component={RouterLink} to={`/videos/${data.id}`} sx={{ display: 'inline-block', mt: 1.5, fontWeight: 600, color: brand.blueInk }}>
        Ver todos os processamentos deste vídeo
      </Link>
    </Panel>
  )
}
