import type { Operation } from './job'

export interface TranscriptSegment {
  start_seconds: number
  end_seconds: number
  text: string
}

export type CalloutVariant = 'definition' | 'important' | 'curiosity' | 'warning' | 'reflection'

export interface ParagraphBlock {
  type: 'paragraph'
  text: string
}

export interface CalloutBlock {
  type: 'callout'
  variant: CalloutVariant
  title: string
  text: string
}

export interface FlowBlock {
  type: 'flow'
  title: string
  steps: { label: string; detail?: string | null }[]
}

export interface CycleBlock {
  type: 'cycle'
  title: string
  stages: string[]
  center?: string | null
}

export interface ComparisonBlock {
  type: 'comparison'
  title: string
  columns: [ComparisonColumn, ComparisonColumn]
  shared?: string | null
}

export interface ComparisonColumn {
  heading: string
  items: string[]
}

export interface TreeBlock {
  type: 'tree'
  title: string
  root: string
  branches: { label: string; children: string[] }[]
}

export type KnownBlock =
  | ParagraphBlock
  | CalloutBlock
  | FlowBlock
  | CycleBlock
  | ComparisonBlock
  | TreeBlock

/** Tipos novos do Processing Service chegam aqui e são exibidos como conteúdo indisponível. */
export interface UnknownBlock {
  type: string
}

export type ChapterBlock = KnownBlock | UnknownBlock

export interface Chapter {
  title: string
  start_seconds: number
  end_seconds: number
  blocks?: ChapterBlock[]
}

export interface ModelReference {
  purpose: Operation
  provider: string
  model: string
  version: string
}

/** Schema `JobResult` de `contracts/openapi/job-service.yaml`. */
export interface JobResult {
  job_id: string
  video_id: string
  transcript: TranscriptSegment[]
  summary?: string
  chapters?: Chapter[]
  models: ModelReference[]
  completed_at: string
}

export type TranscriptFormat = 'txt' | 'json' | 'srt'
