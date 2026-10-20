import type { Job, JobStage } from '../types/job'

/** Concluído abre o resultado; os demais estados abrem o acompanhamento. */
export function jobLink(job: Job): string {
  return job.status === 'completed' ? `/jobs/${job.id}/result` : `/jobs/${job.id}`
}

/** Etapas que o worker percorre para as operações pedidas, na ordem do pipeline. */
export function stagesFor(job: Job): JobStage[] {
  const stages: JobStage[] = ['downloading', 'extracting_audio', 'transcribing']
  if (job.operations.includes('summary')) stages.push('summarizing')
  if (job.operations.includes('chapters')) stages.push('creating_chapters')
  stages.push('uploading_artifacts')
  return stages
}
