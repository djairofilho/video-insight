import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded'
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded'
import { Alert, Box, Button, Stack, Typography } from '@mui/material'
import { brand } from '../app/theme'
import { useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router'
import { JobHistory, NoJobsYet } from '../components/job/JobHistory'
import { OperationSelector } from '../components/job/OperationSelector'
import { PageHeader } from '../components/common/PageHeader'
import { Panel } from '../components/common/Panel'
import { ErrorState, LoadingState } from '../components/common/States'
import { UploadStatusChip } from '../components/common/StatusChip'
import { DeleteVideoDialog } from '../components/video/DeleteVideoDialog'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { ApiError } from '../services/apiClient'
import { createJob, listJobs } from '../services/jobService'
import { createPlaybackUrl, getVideo } from '../services/videoService'
import type { Operation } from '../types/job'
import type { Video } from '../types/video'
import { correlationIdOf, describeError, isNotFound } from '../utils/errorMessages'
import { formatBytes } from '../utils/formatBytes'
import { formatDateTime, formatDuration } from '../utils/formatDuration'
import { createIdempotencyKeyStore } from '../utils/idempotency'
import { OPERATION_ORDER } from '../utils/labels'

export function VideoPage() {
  const { videoId = '' } = useParams()
  const video = useAsyncResource(`video:${videoId}`, (signal) => getVideo(videoId, signal))

  if (video.state.status === 'loading') {
    return <LoadingState label="Carregando o vídeo…" />
  }
  if (video.state.status === 'error') {
    return (
      <>
        <PageHeader title="Vídeo" back={{ to: '/videos', label: 'Meus vídeos' }} />
        <ErrorState
          error={video.state.error}
          title={isNotFound(video.state.error) ? 'Vídeo não encontrado' : 'Não foi possível carregar o vídeo'}
          onRetry={isNotFound(video.state.error) ? undefined : video.reload}
        />
      </>
    )
  }
  return <VideoDetails video={video.state.data} />
}

function VideoDetails({ video }: { video: Video }) {
  const navigate = useNavigate()
  const location = useLocation()
  const justUploaded = (location.state as { uploaded?: boolean } | null)?.uploaded === true
  const [deleting, setDeleting] = useState(false)

  const facts = [
    formatDuration(video.duration_seconds),
    formatBytes(video.size_bytes),
    `enviado em ${formatDateTime(video.created_at)}`,
  ]

  return (
    <>
      <PageHeader
        title={video.file_name}
        description={facts.join(' · ')}
        back={{ to: '/videos', label: 'Meus vídeos' }}
        actions={
          <>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <UploadStatusChip status={video.upload_status} />
            </Box>
            <Button color="inherit" startIcon={<DeleteOutlineRoundedIcon />} onClick={() => setDeleting(true)} sx={{ color: brand.muted }}>
              Excluir
            </Button>
          </>
        }
      />

      {justUploaded && video.upload_status === 'ready' && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Vídeo enviado. Agora escolha o que você quer gerar.
        </Alert>
      )}

      <Box
        sx={{ display: 'grid', gap: 3, gridTemplateColumns: { xs: '1fr', md: '7fr 5fr' }, alignItems: 'start' }}
      >
        <Stack spacing={3} sx={{ minWidth: 0 }}>
          <VideoPreview video={video} />
          <Panel title="Processamentos" titleId="history-title">
            <JobsOfVideo videoId={video.id} />
          </Panel>
        </Stack>
        <Stack spacing={3} sx={{ minWidth: 0, position: { md: 'sticky' }, top: { md: 92 } }}>
          {video.upload_status === 'ready' ? (
            <ProcessForm videoId={video.id} />
          ) : (
            <Alert severity={video.upload_status === 'failed' ? 'error' : 'warning'} variant="outlined">
              {video.upload_status === 'failed'
                ? 'O envio deste vídeo falhou. Exclua-o e envie o arquivo novamente.'
                : 'O envio deste vídeo não foi concluído. Exclua-o e envie o arquivo novamente para processá-lo.'}
            </Alert>
          )}
        </Stack>
      </Box>

      <DeleteVideoDialog
        video={deleting ? video : null}
        onClose={() => setDeleting(false)}
        onDeleted={() => void navigate('/videos', { replace: true })}
      />
    </>
  )
}

/** Prévia do vídeo pela URL temporária de reprodução; antes do upload confirmado, um quadro neutro explica o motivo. */
function VideoPreview({ video }: { video: Video }) {
  const ready = video.upload_status === 'ready'
  const playback = useAsyncResource(`playback:${video.id}:${ready}`, () =>
    ready ? createPlaybackUrl(video.id).then((signed) => signed.url) : Promise.resolve(null),
  )
  const url = playback.state.status === 'success' ? playback.state.data : null

  return (
    <Box sx={{ borderRadius: '12px', overflow: 'hidden', bgcolor: brand.ink, aspectRatio: '16 / 9', display: 'grid', placeItems: 'center' }}>
      {url ? (
        <Box component="video" src={`${url}#t=0.1`} controls preload="metadata" playsInline aria-label={`Prévia de ${video.file_name}`} sx={{ width: '100%', height: '100%', display: 'block' }} />
      ) : (
        <Typography sx={{ color: '#c9d1df', px: 3, textAlign: 'center' }}>
          {playback.state.status === 'loading' && ready
            ? 'Carregando a prévia…'
            : ready
              ? 'Não foi possível carregar a prévia agora.'
              : 'A prévia aparece quando o envio for confirmado.'}
        </Typography>
      )}
    </Box>
  )
}

function ProcessForm({ videoId }: { videoId: string }) {
  const navigate = useNavigate()
  const [operations, setOperations] = useState<Operation[]>([...OPERATION_ORDER])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [keys] = useState(createIdempotencyKeyStore)

  const submit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const job = await createJob(videoId, operations, keys.current())
      keys.reset()
      void navigate(`/jobs/${job.id}`)
    } catch (failure) {
      // Sem resposta do servidor o pedido pode ter sido criado: a nova tentativa reaproveita a mesma chave.
      if (!(failure instanceof ApiError && failure.status === 0)) {
        keys.reset()
      }
      setError(failure)
      setSubmitting(false)
    }
  }

  return (
    <Panel title="Processar este vídeo" titleId="process-title" accent="blue">
      <OperationSelector
        value={operations}
        disabled={submitting}
        onChange={(next) => {
          keys.reset()
          setOperations(next)
        }}
      />
      {error !== null && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {describeError(error)}
          {correlationIdOf(error) && (
            <Typography variant="caption" component="p" sx={{ opacity: 0.8 }}>
              Código da requisição: {correlationIdOf(error)}
            </Typography>
          )}
        </Alert>
      )}
      <Stack spacing={1.25} sx={{ mt: 2.5 }}>
        <Button
          variant="contained"
          size="large"
          fullWidth
          startIcon={<PlayArrowRoundedIcon />}
          disabled={operations.length === 0}
          loading={submitting}
          onClick={() => void submit()}
        >
          Processar vídeo
        </Button>
        <Typography variant="body2" sx={{ color: brand.muted, textAlign: 'center' }}>
          {operations.length === 0
            ? 'Escolha pelo menos uma opção.'
            : 'Roda em segundo plano: você acompanha o andamento na próxima tela.'}
        </Typography>
      </Stack>
    </Panel>
  )
}

function JobsOfVideo({ videoId }: { videoId: string }) {
  const jobs = useAsyncResource(`jobs:${videoId}`, (signal) => listJobs(videoId, undefined, 20, signal))
  if (jobs.state.status === 'loading') {
    return <Typography variant="body2" role="status" sx={{ color: brand.muted }}>Carregando processamentos…</Typography>
  }
  if (jobs.state.status === 'error') {
    return <ErrorState error={jobs.state.error} title="Não foi possível carregar os processamentos" onRetry={jobs.reload} />
  }
  const { items, next_cursor: nextCursor } = jobs.state.data
  if (items.length === 0) {
    return <NoJobsYet />
  }
  return (
    <>
      <JobHistory jobs={items} />
      {nextCursor && (
        <Typography variant="body2" sx={{ color: brand.faint, mt: 1 }}>
          Mostrando os 20 processamentos mais recentes.
        </Typography>
      )}
    </>
  )
}
