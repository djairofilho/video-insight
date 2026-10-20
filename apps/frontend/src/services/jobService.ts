import type { ExportUrl } from '../types/api'
import type { Job, JobPage, Operation } from '../types/job'
import type { JobResult, TranscriptFormat } from '../types/result'
import { apiRequest } from './apiClient'

export function createJob(videoId: string, operations: Operation[], idempotencyKey: string): Promise<Job> {
  return apiRequest<Job>(`/videos/${videoId}/jobs`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    json: { operations },
  })
}

export function listJobs(videoId: string, cursor?: string, limit = 20, signal?: AbortSignal): Promise<JobPage> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (cursor) {
    params.set('cursor', cursor)
  }
  return apiRequest<JobPage>(`/videos/${videoId}/jobs?${params}`, { signal })
}

export function getJob(jobId: string, signal?: AbortSignal): Promise<Job> {
  return apiRequest<Job>(`/jobs/${jobId}`, { signal })
}

export function cancelJob(jobId: string): Promise<Job> {
  return apiRequest<Job>(`/jobs/${jobId}/cancel`, { method: 'POST' })
}

export function retryJob(jobId: string): Promise<Job> {
  return apiRequest<Job>(`/jobs/${jobId}/retry`, { method: 'POST' })
}

export function getJobResult(jobId: string, signal?: AbortSignal): Promise<JobResult> {
  return apiRequest<JobResult>(`/jobs/${jobId}/result`, { signal })
}

export function exportTranscript(jobId: string, format: TranscriptFormat): Promise<ExportUrl> {
  return apiRequest<ExportUrl>(`/jobs/${jobId}/transcript?format=${format}`)
}
