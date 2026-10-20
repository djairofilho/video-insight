import { act, renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { completedJob } from '../mocks/fixtures'
import { API } from '../mocks/handlers'
import { server } from '../test/server'
import type { Job, JobStatus } from '../types/job'
import { useJobPolling } from './useJobPolling'

const JOB = 'job-em-andamento'

function respondWith(statuses: JobStatus[]) {
  const calls: number[] = []
  server.use(
    http.get(`${API}/jobs/${JOB}`, () => {
      calls.push(Date.now())
      const status = statuses[Math.min(calls.length - 1, statuses.length - 1)]
      return HttpResponse.json({ ...completedJob, id: JOB, status } satisfies Job)
    }),
  )
  return calls
}

describe('useJobPolling', () => {
  it('consulta até o estado final e para', async () => {
    const calls = respondWith(['queued', 'processing', 'completed'])
    const { result } = renderHook(() => useJobPolling(JOB, 10))

    await waitFor(() => expect(result.current.job?.status).toBe('completed'))
    await new Promise((resolve) => setTimeout(resolve, 60))
    expect(calls).toHaveLength(3)
  })

  it('não sobrepõe requisições quando a API está lenta', async () => {
    let inFlight = 0
    let maxInFlight = 0
    let count = 0
    server.use(
      http.get(`${API}/jobs/${JOB}`, async () => {
        inFlight += 1
        maxInFlight = Math.max(maxInFlight, inFlight)
        await new Promise((resolve) => setTimeout(resolve, 30))
        inFlight -= 1
        count += 1
        return HttpResponse.json({ ...completedJob, id: JOB, status: count < 4 ? 'processing' : 'completed' })
      }),
    )
    const { result } = renderHook(() => useJobPolling(JOB, 1))

    await waitFor(() => expect(result.current.job?.status).toBe('completed'))
    expect(maxInFlight).toBe(1)
  })

  it('cancela o timer ao desmontar', async () => {
    const calls = respondWith(['processing'])
    const { unmount } = renderHook(() => useJobPolling(JOB, 20))

    await waitFor(() => expect(calls.length).toBeGreaterThan(0))
    unmount()
    const atUnmount = calls.length
    await new Promise((resolve) => setTimeout(resolve, 80))
    expect(calls).toHaveLength(atUnmount)
  })

  it('continua tentando após falha de rede e para em 404', async () => {
    let attempt = 0
    server.use(
      http.get(`${API}/jobs/${JOB}`, () => {
        attempt += 1
        return attempt === 1 ? HttpResponse.error() : HttpResponse.json({ ...completedJob, id: JOB })
      }),
    )
    const { result } = renderHook(() => useJobPolling(JOB, 5))
    await waitFor(() => expect(result.current.job?.status).toBe('completed'))

    vi.spyOn(console, 'error').mockImplementation(() => {})
    let notFound = 0
    server.use(
      http.get(`${API}/jobs/sumiu`, () => {
        notFound += 1
        return HttpResponse.json({ code: 'JOB_NOT_FOUND', message: 'x', correlation_id: 'c' }, { status: 404 })
      }),
    )
    const missing = renderHook(() => useJobPolling('sumiu', 5))
    await waitFor(() => expect(missing.result.current.error).toBeDefined())
    await new Promise((resolve) => setTimeout(resolve, 40))
    expect(notFound).toBe(1)
  })

  it('reinicia o polling depois de uma nova tentativa', async () => {
    const calls = respondWith(['failed', 'processing', 'completed'])
    const { result } = renderHook(() => useJobPolling(JOB, 10))
    await waitFor(() => expect(result.current.job?.status).toBe('failed'))

    act(() => result.current.restart({ ...completedJob, id: JOB, status: 'queued', attempt: 2 }))
    expect(result.current.job?.status).toBe('queued')
    await waitFor(() => expect(result.current.job?.status).toBe('completed'))
    expect(calls).toHaveLength(3)
  })
})
