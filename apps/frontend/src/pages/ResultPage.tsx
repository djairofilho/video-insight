import { Alert, Box, Stack, Typography } from '@mui/material'
import { Fragment, useRef, useState } from 'react'
import { Navigate, useParams } from 'react-router'
import { brand } from '../app/theme'
import { PageHeader } from '../components/common/PageHeader'
import { Panel } from '../components/common/Panel'
import { ErrorState, LoadingState } from '../components/common/States'
import { ChapterList } from '../components/result/ChapterList'
import { ChapterTimeline } from '../components/result/ChapterTimeline'
import { ChapterArticle, SummaryCard } from '../components/result/ResultContent'
import { TranscriptPanel } from '../components/result/TranscriptPanel'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { getJob, getJobResult } from '../services/jobService'
import { createPlaybackUrl, getVideo } from '../services/videoService'
import type { Job } from '../types/job'
import type { JobResult } from '../types/result'
import type { Video } from '../types/video'
import { isNotFound } from '../utils/errorMessages'
import { findActiveIndex } from '../utils/findActiveIndex'
import { formatDateTime } from '../utils/formatDuration'
import { formatTimestamp } from '../utils/formatTimestamp'

type Loaded =
  | { kind: 'pending' }
  | { kind: 'ready'; job: Job; result: JobResult; playbackUrl: string | null; video?: Video }

async function loadResult(jobId: string, signal: AbortSignal): Promise<Loaded> {
  const job = await getJob(jobId, signal)
  if (job.status !== 'completed') {
    return { kind: 'pending' }
  }
  const [result, playback, video] = await Promise.all([
    getJobResult(jobId, signal),
    // Sem o vídeo (por exemplo, excluído) o resultado ainda pode ser consultado.
    createPlaybackUrl(job.video_id).catch(() => null),
    getVideo(job.video_id, signal).catch(() => undefined),
  ])
  return { kind: 'ready', job, result, playbackUrl: playback?.url ?? null, video }
}

export function ResultPage() {
  const { jobId = '' } = useParams()
  const resource = useAsyncResource(`result:${jobId}`, (signal) => loadResult(jobId, signal))
  const { state } = resource

  if (state.status === 'loading') {
    return <LoadingState label="Carregando o resultado…" />
  }
  if (state.status === 'error') {
    return (
      <>
        <PageHeader title="Resultado" back={{ to: '/videos', label: 'Meus vídeos' }} />
        <ErrorState
          error={state.error}
          title={isNotFound(state.error) ? 'Resultado não encontrado' : 'O resultado está temporariamente indisponível'}
          onRetry={isNotFound(state.error) ? undefined : resource.reload}
        />
      </>
    )
  }
  if (state.data.kind === 'pending') {
    return <Navigate to={`/jobs/${jobId}`} replace />
  }
  return <ResultView {...state.data} />
}

interface ResultViewProps {
  job: Job
  result: JobResult
  playbackUrl: string | null
  video?: Video
}

function ResultView({ job, result, playbackUrl, video }: ResultViewProps) {
  const playerRef = useRef<HTMLVideoElement>(null)
  const [source, setSource] = useState(playbackUrl)
  const [refreshedSource, setRefreshedSource] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)

  const chapters = result.chapters ?? []
  const duration = video?.duration_seconds ?? result.transcript.at(-1)?.end_seconds ?? chapters.at(-1)?.end_seconds ?? 0
  const activeSegment = findActiveIndex(result.transcript, currentTime)
  const activeChapter = findActiveIndex(chapters, currentTime)
  const models = [...new Set(result.models.map((model) => model.model))]

  const seekTo = (seconds: number) => {
    const player = playerRef.current
    if (!player) return
    player.currentTime = seconds
    setCurrentTime(seconds)
    void player.play().catch(() => {})
    const box = player.getBoundingClientRect()
    if (box.top < 0 || box.bottom > window.innerHeight) {
      player.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }

  // A URL de reprodução é temporária: se expirar, pede uma nova uma única vez e retoma do mesmo ponto.
  const onPlayerError = async () => {
    if (refreshedSource) return
    setRefreshedSource(true)
    const resumeAt = playerRef.current?.currentTime ?? 0
    try {
      const fresh = await createPlaybackUrl(job.video_id)
      setSource(fresh.url)
      requestAnimationFrame(() => {
        if (playerRef.current) playerRef.current.currentTime = resumeAt
      })
    } catch {
      setSource(null)
    }
  }

  const facts = [
    duration > 0 ? formatTimestamp(duration) : null,
    chapters.length > 0 ? `${chapters.length} ${chapters.length === 1 ? 'capítulo' : 'capítulos'}` : null,
    `${result.transcript.length} trechos transcritos`,
    `processado em ${formatDateTime(result.completed_at)}`,
  ].filter(Boolean)

  return (
    <>
      <PageHeader
        title={video?.file_name ?? 'Vídeo processado'}
        description={facts.join(' · ')}
        back={{ to: `/videos/${job.video_id}`, label: 'Voltar ao vídeo' }}
      />
      <Box
        sx={{
          display: 'grid',
          gap: 3,
          gridTemplateColumns: { xs: '1fr', md: 'minmax(340px, 5fr) 7fr', lg: 'minmax(400px, 5fr) 7fr' },
          alignItems: 'start',
        }}
      >
        {/* No desktop a coluna cabe na janela: player e capítulos fixos, a transcrição ocupa o resto e rola sozinha. */}
        <Stack
          spacing={2}
          sx={{ position: { md: 'sticky' }, top: { md: 92 }, height: { md: 'calc(100svh - 116px)' }, minHeight: { md: 560 }, minWidth: 0 }}
        >
          <Box sx={{ flexShrink: 0, borderRadius: '12px', overflow: 'hidden', bgcolor: brand.ink, aspectRatio: '16 / 9' }}>
            {source ? (
              <Box
                component="video"
                ref={playerRef}
                src={`${source}#t=0.1`}
                controls
                preload="metadata"
                playsInline
                onTimeUpdate={() => setCurrentTime(playerRef.current?.currentTime ?? 0)}
                onError={() => void onPlayerError()}
                sx={{ width: '100%', height: '100%', display: 'block' }}
                aria-label="Player do vídeo"
              />
            ) : (
              <Stack sx={{ height: '100%', alignItems: 'center', justifyContent: 'center', color: '#c9d1df', p: 3, textAlign: 'center' }}>
                <Typography>O vídeo não está disponível para reprodução.</Typography>
              </Stack>
            )}
          </Box>
          {chapters.length > 0 && (
            <Panel title="Capítulos" titleId="chapters-nav-title" component="nav" sx={{ flexShrink: 0, maxHeight: { md: '40svh' }, overflowY: 'auto' }}>
              <ChapterTimeline
                chapters={chapters}
                duration={duration}
                currentTime={currentTime}
                activeIndex={activeChapter}
                onSeek={seekTo}
              />
              <Box sx={{ mt: 2 }}>
                <ChapterList chapters={chapters} activeIndex={activeChapter} onSeek={seekTo} />
              </Box>
            </Panel>
          )}
          <TranscriptPanel jobId={job.id} segments={result.transcript} activeIndex={activeSegment} onSeek={seekTo} />
        </Stack>

        <Stack spacing={3} sx={{ minWidth: 0 }}>
          {result.summary ? (
            <SummaryCard summary={result.summary} />
          ) : (
            job.operations.includes('summary') && <Alert severity="info">O resumo não foi gerado para este vídeo.</Alert>
          )}

          {chapters.length > 0 ? (
            <Panel sx={{ p: { xs: 2.5, md: 4 } }}>
              <Stack spacing={6} component="section" aria-label="Capítulos em detalhe">
                {chapters.map((chapter, index) => (
                  <Fragment key={`${chapter.start_seconds}-${index}`}>
                    <ChapterArticle chapter={chapter} number={index + 1} playing={index === activeChapter} onSeek={seekTo} />
                  </Fragment>
                ))}
              </Stack>
            </Panel>
          ) : (
            job.operations.includes('chapters') && <Alert severity="info">Os capítulos não foram gerados para este vídeo.</Alert>
          )}

          {models.length > 0 && (
            <Typography variant="caption" component="p" sx={{ color: brand.faint }}>
              Gerado com {models.join(' e ')}. Os textos são produzidos por IA e podem conter imprecisões.
            </Typography>
          )}
        </Stack>
      </Box>
    </>
  )
}
