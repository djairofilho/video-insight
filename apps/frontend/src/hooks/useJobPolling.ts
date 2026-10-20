import { useEffect, useState } from 'react'
import { ApiError } from '../services/apiClient'
import { getJob } from '../services/jobService'
import { isTerminal, type Job } from '../types/job'

export const POLL_INTERVAL_MS = 2500

interface Snapshot {
  jobId: string
  generation: number
  job?: Job
  error?: unknown
}

function shouldKeepPolling(error: unknown): boolean {
  // 404 e 401 não se resolvem sozinhos; falhas de rede e 5xx sim.
  return !(error instanceof ApiError && (error.status === 404 || error.status === 401))
}

/**
 * Acompanha um job por polling, já que os contratos não oferecem atualização em tempo real. A próxima consulta só é
 * agendada depois da resposta (`setTimeout`, não `setInterval`), então nunca há duas requisições ao mesmo tempo. O
 * polling para em `completed`, `failed` ou `cancelled` e é cancelado quando o componente desmonta.
 */
export function useJobPolling(jobId: string, intervalMs = POLL_INTERVAL_MS) {
  const [generation, setGeneration] = useState(0)
  const [snapshot, setSnapshot] = useState<Snapshot>({ jobId, generation: 0 })

  useEffect(() => {
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined

    const poll = async () => {
      try {
        const job = await getJob(jobId, controller.signal)
        if (controller.signal.aborted) return
        setSnapshot({ jobId, generation, job })
        if (!isTerminal(job.status)) {
          timer = setTimeout(poll, intervalMs)
        }
      } catch (error) {
        if (controller.signal.aborted) return
        setSnapshot((previous) => ({
          jobId,
          generation,
          job: previous.jobId === jobId ? previous.job : undefined,
          error,
        }))
        if (shouldKeepPolling(error)) {
          timer = setTimeout(poll, intervalMs * 2)
        }
      }
    }

    void poll()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [jobId, generation, intervalMs])

  const current = snapshot.jobId === jobId ? snapshot : undefined

  return {
    job: current?.job,
    error: current?.error,
    /** Aplica a resposta de cancelar/retentar e reinicia o polling. */
    restart: (job: Job) => {
      const next = generation + 1
      setSnapshot({ jobId, generation: next, job })
      setGeneration(next)
    },
  }
}
