import type { JobStage, JobStatus, Operation } from '../types/job'
import type { UploadStatus } from '../types/video'

export const OPERATION_LABELS: Record<Operation, string> = {
  transcription: 'Transcrição',
  summary: 'Resumo',
  chapters: 'Capítulos',
}

export const OPERATION_ORDER: readonly Operation[] = ['transcription', 'summary', 'chapters']

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  queued: 'Na fila',
  processing: 'Processando',
  completed: 'Concluído',
  failed: 'Falhou',
  cancelled: 'Cancelado',
}

export const JOB_STAGE_LABELS: Record<JobStage, string> = {
  downloading: 'Baixando o vídeo',
  extracting_audio: 'Extraindo o áudio',
  transcribing: 'Transcrevendo',
  summarizing: 'Gerando o resumo',
  creating_chapters: 'Criando os capítulos',
  uploading_artifacts: 'Salvando os resultados',
}

export const UPLOAD_STATUS_LABELS: Record<UploadStatus, string> = {
  pending: 'Aguardando envio',
  uploading: 'Enviando',
  ready: 'Pronto',
  failed: 'Falhou',
}
