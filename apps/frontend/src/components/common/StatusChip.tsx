import { Chip } from '@mui/material'
import { brand } from '../../app/theme'
import type { JobStatus } from '../../types/job'
import type { UploadStatus } from '../../types/video'
import { JOB_STATUS_LABELS, UPLOAD_STATUS_LABELS } from '../../utils/labels'

/** Pares de tom claro com texto escuro da mesma cor; turquesa é a cor de "pronto" da marca. */
const TONES = {
  neutral: { bg: brand.raised, ink: brand.muted },
  progress: { bg: brand.blueTint, ink: brand.blueInk },
  done: { bg: brand.tealTint, ink: brand.tealInk },
  failed: { bg: brand.negativeTint, ink: brand.negativeInk },
} as const

type Tone = keyof typeof TONES

const UPLOAD_TONES: Record<UploadStatus, Tone> = {
  pending: 'neutral',
  uploading: 'progress',
  ready: 'done',
  failed: 'failed',
}

const JOB_TONES: Record<JobStatus, Tone> = {
  queued: 'neutral',
  processing: 'progress',
  completed: 'done',
  failed: 'failed',
  cancelled: 'neutral',
}

function StatusPill({ tone, label }: { tone: Tone; label: string }) {
  const { bg, ink } = TONES[tone]
  return <Chip size="small" label={label} sx={{ bgcolor: bg, color: ink }} />
}

export function UploadStatusChip({ status }: { status: UploadStatus }) {
  return <StatusPill tone={UPLOAD_TONES[status]} label={UPLOAD_STATUS_LABELS[status]} />
}

export function JobStatusChip({ status }: { status: JobStatus }) {
  return <StatusPill tone={JOB_TONES[status]} label={JOB_STATUS_LABELS[status]} />
}
