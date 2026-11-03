import { useEffect, useState } from 'react'
import { ApiError } from '../services/apiClient'
import { getJob } from '../services/jobService'
import { isTerminal, type Job } from '../types/job'

export const POLL_INTERVAL_MS = 2500
export const MAX_POLL_INTERVAL_MS = 15000

interface Snapshot {
  jobId: string
  generation: number
  job?: Job
  error?: unknown
}

function shouldKeepPolling(error: unknown): boolean {
  // 404 e 401 não se resolvem sozinhos; falhas de rede e 5xx sim.
  return !(error instanceof ApiError && [401, 403, 404].includes(error.status))
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
    let inFlight = false
    let stopped = false
    let unchanged = 0
    let lastProgress = ''
    let failures = 0

    const schedule = (delay: number) => {
      if (!document.hidden && !controller.signal.aborted && !stopped) {
        timer = setTimeout(poll, delay)
      }
    }

    const poll = async () => {
      if (document.hidden || inFlight || stopped || controller.signal.aborted) return
      inFlight = true
      try {
        const job = await getJob(jobId, controller.signal)
        if (controller.signal.aborted) return
        failures = 0
        setSnapshot({ jobId, generation, job })
        stopped = isTerminal(job.status)
        if (!stopped) {
          const progress = `${job.status}:${job.stage}:${job.progress_percent}:${job.attempt}`
          unchanged = progress === lastProgress ? unchanged + 1 : 0
          lastProgress = progress
          const factor = job.status === 'queued' ? 3 : Math.min(1 + Math.floor(unchanged / 3), 4)
          schedule(Math.min(intervalMs * factor, MAX_POLL_INTERVAL_MS))
        }
      } catch (error) {
        if (controller.signal.aborted) return
        setSnapshot((previous) => ({
          jobId,
          generation,
          job: previous.jobId === jobId ? previous.job : undefined,
          error,
        }))
        stopped = !shouldKeepPolling(error)
        failures += 1
        schedule(Math.min(intervalMs * 2 ** Math.min(failures, 5), 60000))
      } finally {
        inFlight = false
      }
    }

    const onVisibilityChange = () => {
      clearTimeout(timer)
      if (!document.hidden) void poll()
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
    void poll()
    return () => {
      controller.abort()
      clearTimeout(timer)
      document.removeEventListener('visibilitychange', onVisibilityChange)
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
