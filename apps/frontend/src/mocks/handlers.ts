import { delay, http, HttpResponse } from 'msw'
import type { Job, JobStage, Operation } from '../types/job'
import type { Video } from '../types/video'
import { completedJob, JOB_ID, jobResult, libraryVideos, readyVideo, VIDEO_ID } from './fixtures'

export const API = 'http://gateway.test/api/v1'
export const STORAGE = 'http://storage.test'
const SAMPLE_VIDEO = 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'

const PIPELINE: { stage: JobStage; progress: number }[] = [
  { stage: 'downloading', progress: 10 },
  { stage: 'extracting_audio', progress: 25 },
  { stage: 'transcribing', progress: 55 },
  { stage: 'summarizing', progress: 75 },
  { stage: 'creating_chapters', progress: 90 },
  { stage: 'uploading_artifacts', progress: 97 },
]

function error(status: number, code: string, message: string) {
  return HttpResponse.json({ code, message, correlation_id: crypto.randomUUID() }, { status })
}

/**
 * Gateway simulado em memória. Um job novo avança uma etapa a cada consulta até concluir, o que permite ver o
 * fluxo completo (upload → processamento → resultado) sem os serviços.
 */
export function createHandlers(apiBase = API) {
  const videos = new Map<string, Video>([[VIDEO_ID, readyVideo], ...libraryVideos.map((video): [string, Video] => [video.id, video])])
  const jobs = new Map<string, Job>([[JOB_ID, completedJob]])
  const ticks = new Map<string, number>()
  const now = () => new Date().toISOString()

  return [
    http.get(`${apiBase}/videos`, () => {
      const items = [...videos.values()].sort((a, b) => b.created_at.localeCompare(a.created_at))
      return HttpResponse.json({ items })
    }),
    http.post(`${apiBase}/videos`, async ({ request }) => {
      const body = (await request.json()) as { file_name: string; size_bytes: number }
      const video: Video = {
        id: crypto.randomUUID(),
        file_name: body.file_name,
        content_type: 'video/mp4',
        size_bytes: body.size_bytes,
        upload_status: 'pending',
        created_at: now(),
      }
      videos.set(video.id, video)
      return HttpResponse.json(video, { status: 201 })
    }),
    http.get(`${apiBase}/videos/:videoId`, ({ params }) => {
      const video = videos.get(String(params.videoId))
      return video ? HttpResponse.json(video) : error(404, 'VIDEO_NOT_FOUND', 'Vídeo não encontrado.')
    }),
    http.delete(`${apiBase}/videos/:videoId`, ({ params }) => {
      videos.delete(String(params.videoId))
      return new HttpResponse(null, { status: 204 })
    }),
    http.post(`${apiBase}/videos/:videoId/upload-url`, ({ params }) => {
      const video = videos.get(String(params.videoId))
      if (!video) return error(404, 'VIDEO_NOT_FOUND', 'Vídeo não encontrado.')
      videos.set(video.id, { ...video, upload_status: 'uploading' })
      return HttpResponse.json({
        url: `${STORAGE}/videos/${video.id}/original.mp4?X-Amz-Signature=mock`,
        method: 'PUT',
        expires_at: new Date(Date.now() + 15 * 60_000).toISOString(),
        headers: { 'Content-Type': 'video/mp4' },
      })
    }),
    http.put(`${STORAGE}/videos/:videoId/original.mp4`, async () => {
      await delay(600)
      return new HttpResponse(null, { status: 200 })
    }),
    http.post(`${apiBase}/videos/:videoId/upload-complete`, async ({ params, request }) => {
      const video = videos.get(String(params.videoId))
      if (!video) return error(404, 'VIDEO_NOT_FOUND', 'Vídeo não encontrado.')
      const body = (await request.json()) as { duration_seconds: number }
      const ready: Video = { ...video, upload_status: 'ready', duration_seconds: body.duration_seconds, updated_at: now() }
      videos.set(ready.id, ready)
      return HttpResponse.json(ready)
    }),
    http.post(`${apiBase}/videos/:videoId/playback-url`, () =>
      HttpResponse.json({ url: SAMPLE_VIDEO, method: 'GET', expires_at: new Date(Date.now() + 15 * 60_000).toISOString() }),
    ),
    http.get(`${apiBase}/videos/:videoId/jobs`, ({ params }) => {
      const items = [...jobs.values()]
        .filter((job) => job.video_id === params.videoId)
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
      return HttpResponse.json({ items })
    }),
    http.post(`${apiBase}/videos/:videoId/jobs`, async ({ params, request }) => {
      const video = videos.get(String(params.videoId))
      if (!video) return error(404, 'VIDEO_NOT_FOUND', 'Vídeo não encontrado.')
      if (video.upload_status !== 'ready') return error(409, 'VIDEO_NOT_READY', 'O upload do vídeo ainda não foi confirmado.')
      const body = (await request.json()) as { operations: Operation[] }
      const job: Job = {
        id: crypto.randomUUID(),
        video_id: video.id,
        operations: body.operations,
        status: 'queued',
        progress_percent: 0,
        attempt: 1,
        created_at: now(),
        updated_at: now(),
      }
      jobs.set(job.id, job)
      ticks.set(job.id, 0)
      return HttpResponse.json(job, { status: 202 })
    }),
    http.get(`${apiBase}/jobs/:jobId`, ({ params }) => {
      const job = jobs.get(String(params.jobId))
      if (!job) return error(404, 'JOB_NOT_FOUND', 'Job não encontrado.')
      if (job.status === 'queued' || job.status === 'processing') {
        const tick = (ticks.get(job.id) ?? 0) + 1
        ticks.set(job.id, tick)
        const step = PIPELINE[tick - 1]
        const next: Job = step
          ? { ...job, status: 'processing', stage: step.stage, progress_percent: step.progress, updated_at: now() }
          : { ...job, status: 'completed', progress_percent: 100, updated_at: now() }
        jobs.set(job.id, next)
        return HttpResponse.json(next)
      }
      return HttpResponse.json(job)
    }),
    http.post(`${apiBase}/jobs/:jobId/cancel`, ({ params }) => {
      const job = jobs.get(String(params.jobId))
      if (!job) return error(404, 'JOB_NOT_FOUND', 'Job não encontrado.')
      if (job.status !== 'queued' && job.status !== 'processing') {
        return error(409, 'INVALID_JOB_STATE', 'O job já foi finalizado.')
      }
      const cancelled: Job = { ...job, status: 'cancelled', updated_at: now() }
      jobs.set(job.id, cancelled)
      return HttpResponse.json(cancelled, { status: 202 })
    }),
    http.post(`${apiBase}/jobs/:jobId/retry`, ({ params }) => {
      const job = jobs.get(String(params.jobId))
      if (!job) return error(404, 'JOB_NOT_FOUND', 'Job não encontrado.')
      if (job.status !== 'failed') return error(409, 'INVALID_JOB_STATE', 'Só jobs com falha podem ser repetidos.')
      const retried: Job = { ...job, status: 'queued', stage: undefined, error: undefined, progress_percent: 0, attempt: job.attempt + 1, updated_at: now() }
      jobs.set(job.id, retried)
      ticks.set(job.id, 0)
      return HttpResponse.json(retried, { status: 202 })
    }),
    http.get(`${apiBase}/jobs/:jobId/result`, ({ params }) => {
      const job = jobs.get(String(params.jobId))
      if (!job) return error(404, 'JOB_NOT_FOUND', 'Job não encontrado.')
      if (job.status !== 'completed') return error(409, 'JOB_NOT_COMPLETED', 'O job ainda não foi concluído.')
      return HttpResponse.json({ ...jobResult, job_id: job.id, video_id: job.video_id })
    }),
    http.get(`${apiBase}/jobs/:jobId/transcript`, ({ request }) => {
      const format = new URL(request.url).searchParams.get('format')
      return HttpResponse.json({
        url: `data:text/plain;charset=utf-8,${encodeURIComponent(`Transcrição de exemplo (${format}).`)}`,
        expires_at: new Date(Date.now() + 15 * 60_000).toISOString(),
      })
    }),
  ]
}
