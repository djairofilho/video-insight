import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { completedJob, JOB_ID, readyVideo, VIDEO_ID } from '../mocks/fixtures'
import { API } from '../mocks/handlers'
import { renderRoute } from '../test/render'
import { server } from '../test/server'
import type { Job } from '../types/job'
import type { Video } from '../types/video'

function apiError(status: number, code: string) {
  return HttpResponse.json({ code, message: code, correlation_id: 'corr-test' }, { status })
}

describe('Meus vídeos', () => {
  it('lista os vídeos com tamanho, duração e estado', async () => {
    renderRoute('/videos')
    const table = await screen.findByRole('table', { name: 'Vídeos enviados' })
    const row = within(table).getByRole('row', { name: /aula-fotossintese\.mp4/ })
    expect(row).toHaveTextContent('46 MB')
    expect(row).toHaveTextContent('3 min 15 s')
    expect(row).toHaveTextContent('Pronto')
  })

  it('mostra o estado vazio sem tratar a lista vazia como erro', async () => {
    server.use(http.get(`${API}/videos`, () => HttpResponse.json({ items: [] })))
    renderRoute('/videos')
    expect(await screen.findByText('Nenhum vídeo por aqui')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('permite tentar de novo depois de um erro', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    let calls = 0
    server.use(
      http.get(`${API}/videos`, () => {
        calls += 1
        return calls === 1 ? apiError(500, 'INTERNAL_ERROR') : HttpResponse.json({ items: [readyVideo] })
      }),
    )
    renderRoute('/videos')
    await userEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }))
    expect(await screen.findByRole('link', { name: 'aula-fotossintese.mp4' })).toBeInTheDocument()
  })

  it('pagina pelo next_cursor', async () => {
    const second: Video = { ...readyVideo, id: 'segundo', file_name: 'entrevista.mp4' }
    server.use(
      http.get(`${API}/videos`, ({ request }) => {
        const cursor = new URL(request.url).searchParams.get('cursor')
        return HttpResponse.json(cursor === 'pagina-2' ? { items: [second] } : { items: [readyVideo], next_cursor: 'pagina-2' })
      }),
    )
    renderRoute('/videos')
    await userEvent.click(await screen.findByRole('button', { name: 'Carregar mais' }))
    expect(await screen.findByRole('link', { name: 'entrevista.mp4' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Carregar mais' })).not.toBeInTheDocument()
  })

  it('exclui um vídeo depois da confirmação', async () => {
    let deleted: string | undefined
    server.use(
      http.delete(`${API}/videos/:videoId`, ({ params }) => {
        deleted = String(params.videoId)
        return new HttpResponse(null, { status: 204 })
      }),
    )
    renderRoute('/videos')
    await userEvent.click(await screen.findByRole('button', { name: 'Excluir aula-fotossintese.mp4' }))
    const dialog = await screen.findByRole('dialog', { name: 'Excluir vídeo?' })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Excluir' }))

    await waitFor(() => expect(screen.queryByRole('link', { name: 'aula-fotossintese.mp4' })).not.toBeInTheDocument())
    expect(deleted).toBe(VIDEO_ID)
  })
})

describe('Vídeo e criação do job', () => {
  it('cria o job com Idempotency-Key e abre o acompanhamento', async () => {
    let request: { key: string | null; body: unknown } | undefined
    server.use(
      http.post(`${API}/videos/:videoId/jobs`, async ({ request: incoming }) => {
        request = { key: incoming.headers.get('idempotency-key'), body: await incoming.json() }
        return HttpResponse.json({ ...completedJob, id: 'novo-job', status: 'queued' } satisfies Job, { status: 202 })
      }),
    )
    const { router } = renderRoute(`/videos/${VIDEO_ID}`)

    await userEvent.click(await screen.findByRole('checkbox', { name: /Capítulos/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Processar vídeo' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/jobs/novo-job'))
    expect(request?.body).toEqual({ operations: ['transcription', 'summary'] })
    expect(request?.key?.length).toBeGreaterThanOrEqual(16)
  })

  it('exige ao menos uma operação', async () => {
    renderRoute(`/videos/${VIDEO_ID}`)
    for (const name of [/Transcrição/, /Resumo/, /Capítulos/]) {
      await userEvent.click(await screen.findByRole('checkbox', { name }))
    }
    expect(screen.getByRole('button', { name: 'Processar vídeo' })).toBeDisabled()
    expect(screen.getByText('Escolha pelo menos uma opção.')).toBeInTheDocument()
  })

  it('reaproveita a chave quando a requisição falha por rede', async () => {
    const keys: (string | null)[] = []
    server.use(
      http.post(`${API}/videos/:videoId/jobs`, ({ request }) => {
        keys.push(request.headers.get('idempotency-key'))
        return keys.length === 1
          ? HttpResponse.error()
          : HttpResponse.json({ ...completedJob, id: 'job-repetido', status: 'queued' }, { status: 202 })
      }),
    )
    const { router } = renderRoute(`/videos/${VIDEO_ID}`)

    await userEvent.click(await screen.findByRole('button', { name: 'Processar vídeo' }))
    expect(await screen.findByText(/Não foi possível conectar/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Processar vídeo' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/jobs/job-repetido'))
    expect(keys).toHaveLength(2)
    expect(keys[1]).toBe(keys[0])
  })

  it('não permite processar um vídeo que não está pronto', async () => {
    server.use(http.get(`${API}/videos/:videoId`, () => HttpResponse.json({ ...readyVideo, upload_status: 'uploading' })))
    renderRoute(`/videos/${VIDEO_ID}`)
    expect(await screen.findByText(/não foi concluído/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Processar vídeo' })).not.toBeInTheDocument()
  })

  it('lista os processamentos anteriores do vídeo', async () => {
    renderRoute(`/videos/${VIDEO_ID}`)
    const history = await screen.findByRole('list', { name: 'Processamentos deste vídeo' })
    expect(within(history).getByRole('link')).toHaveAttribute('href', `/jobs/${JOB_ID}/result`)
  })
})

describe('Acompanhamento do job', () => {
  it('oferece nova tentativa para falha recuperável', async () => {
    const failed: Job = {
      ...completedJob,
      status: 'failed',
      stage: 'transcribing',
      error: { code: 'STT_TIMEOUT', message: 'Tempo esgotado na transcrição.', retryable: true },
    }
    let retried = false
    server.use(
      http.get(`${API}/jobs/:jobId`, () => HttpResponse.json(retried ? { ...failed, status: 'processing', error: undefined, attempt: 2 } : failed)),
      http.post(`${API}/jobs/:jobId/retry`, () => {
        retried = true
        return HttpResponse.json({ ...failed, status: 'queued', error: undefined, attempt: 2 }, { status: 202 })
      }),
    )
    renderRoute(`/jobs/${JOB_ID}`)

    expect(await screen.findByText('Tempo esgotado na transcrição.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(await screen.findByText(/Tentativa 2/)).toBeInTheDocument()
    expect(retried).toBe(true)
  })

  it('não oferece nova tentativa para falha não recuperável', async () => {
    server.use(
      http.get(`${API}/jobs/:jobId`, () =>
        HttpResponse.json({ ...completedJob, status: 'failed', error: { code: 'INVALID_MEDIA', message: 'Arquivo corrompido.', retryable: false } }),
      ),
    )
    renderRoute(`/jobs/${JOB_ID}`)
    expect(await screen.findByText('Arquivo corrompido.')).toBeInTheDocument()
    expect(screen.getByText(/não se resolve com uma nova tentativa/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Tentar novamente' })).not.toBeInTheDocument()
  })

  it('cancela um job em andamento após confirmação', async () => {
    const running: Job = { ...completedJob, status: 'processing', stage: 'transcribing', progress_percent: 55 }
    let cancelled = false
    server.use(
      http.get(`${API}/jobs/:jobId`, () => HttpResponse.json(cancelled ? { ...running, status: 'cancelled' } : running)),
      http.post(`${API}/jobs/:jobId/cancel`, () => {
        cancelled = true
        return HttpResponse.json({ ...running, status: 'cancelled' }, { status: 202 })
      }),
    )
    renderRoute(`/jobs/${JOB_ID}`)

    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar processamento' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancelar processamento' }))
    expect(await screen.findByText('Processamento cancelado')).toBeInTheDocument()
  })

  it('leva ao resultado quando o job termina', async () => {
    renderRoute(`/jobs/${JOB_ID}`)
    expect(await screen.findByRole('link', { name: 'Ver resultado' })).toHaveAttribute('href', `/jobs/${JOB_ID}/result`)
  })
})

describe('Resultado', () => {
  it('mostra player, resumo, capítulos e transcrição na mesma tela', async () => {
    renderRoute(`/jobs/${JOB_ID}/result`)

    expect(await screen.findByRole('heading', { name: 'Resumo' })).toBeInTheDocument()
    expect(screen.getByLabelText('Player do vídeo')).toHaveAttribute('src', expect.stringContaining('flower.mp4'))
    expect(screen.getByRole('heading', { name: 'O ciclo do carbono e reflexão final', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Trechos da transcrição' })).toHaveTextContent('Olá, turma!')
    expect(screen.getByText(/Gerado com whisper-large-v3-turbo/)).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Linha do tempo dos capítulos' })).toBeInTheDocument()
  })

  it('redireciona para o acompanhamento se o job não terminou', async () => {
    server.use(http.get(`${API}/jobs/:jobId`, () => HttpResponse.json({ ...completedJob, status: 'processing' })))
    const { router } = renderRoute(`/jobs/${JOB_ID}/result`)
    await waitFor(() => expect(router.state.location.pathname).toBe(`/jobs/${JOB_ID}`))
  })

  it('pede uma URL temporária nova a cada exportação', async () => {
    const formats: (string | null)[] = []
    server.use(
      http.get(`${API}/jobs/:jobId/transcript`, ({ request }) => {
        formats.push(new URL(request.url).searchParams.get('format'))
        return HttpResponse.json({ url: 'http://storage.test/t.srt', expires_at: '2026-10-19T15:00:00Z' })
      }),
    )
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    renderRoute(`/jobs/${JOB_ID}/result`)

    await userEvent.click(await screen.findByRole('button', { name: 'Baixar transcrição em SRT' }))
    await userEvent.click(screen.getByRole('button', { name: 'Baixar transcrição em TXT' }))
    await waitFor(() => expect(click).toHaveBeenCalledTimes(2))
    expect(formats).toEqual(['srt', 'txt'])
  })

  it('explica quando o resultado está temporariamente indisponível', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    server.use(http.get(`${API}/jobs/:jobId/result`, () => apiError(503, 'INTERNAL_ERROR')))
    renderRoute(`/jobs/${JOB_ID}/result`)
    expect(await screen.findByText('O resultado está temporariamente indisponível')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
  })
})
