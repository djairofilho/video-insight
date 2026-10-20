import type { CursorPage } from './api'

export type Operation = 'transcription' | 'summary' | 'chapters'

export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled'

export type JobStage =
  | 'downloading'
  | 'extracting_audio'
  | 'transcribing'
  | 'summarizing'
  | 'creating_chapters'
  | 'uploading_artifacts'

export interface JobError {
  code: string
  message: string
  retryable: boolean
}

/** Schema `Job` de `contracts/openapi/job-service.yaml`. */
export interface Job {
  id: string
  video_id: string
  operations: Operation[]
  status: JobStatus
  stage?: JobStage
  progress_percent: number
  attempt: number
  error?: JobError
  created_at: string
  updated_at: string
}

export type JobPage = CursorPage<Job>

export const TERMINAL_STATUSES: readonly JobStatus[] = ['completed', 'failed', 'cancelled']

export function isTerminal(status: JobStatus): boolean {
  return TERMINAL_STATUSES.includes(status)
}
