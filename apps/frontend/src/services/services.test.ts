import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { API } from '../mocks/handlers'
import { server } from '../test/server'
import { ApiError, apiRequest } from './apiClient'
import { setAccessTokenProvider, setUnauthorizedHandler } from './authService'
import { createJob } from './jobService'
import { uploadToSignedUrl, UploadError } from './videoService'

afterEach(() => {
  setAccessTokenProvider(async () => null)
  setUnauthorizedHandler(() => {})
})

describe('apiRequest', () => {
  it('prefixa a URL do Gateway e envia JSON', async () => {
    let received: { url: string; contentType: string | null; body: unknown } | undefined
    server.use(
      http.post(`${API}/eco`, async ({ request }) => {
        received = { url: request.url, contentType: request.headers.get('content-type'), body: await request.json() }
        return HttpResponse.json({ ok: true })
      }),
    )

    await expect(apiRequest('/eco', { method: 'POST', json: { a: 1 } })).resolves.toEqual({ ok: true })
    expect(received).toEqual({ url: `${API}/eco`, contentType: 'application/json', body: { a: 1 } })
  })

  it('anexa o access token quando há sessão', async () => {
    let authorization: string | null = null
    server.use(
      http.get(`${API}/eco`, ({ request }) => {
        authorization = request.headers.get('authorization')
        return HttpResponse.json({})
      }),
    )

    await apiRequest('/eco')
    expect(authorization).toBeNull()

    setAccessTokenProvider(async () => 'token-123')
    await apiRequest('/eco')
    expect(authorization).toBe('Bearer token-123')
  })

  it('converte respostas de erro em ApiError com code e correlation_id', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    server.use(
      http.get(`${API}/eco`, () =>
        HttpResponse.json({ code: 'VIDEO_NOT_READY', message: 'Não pronto', correlation_id: 'corr-1' }, { status: 409 }),
      ),
    )

    const error = await apiRequest('/eco').catch((failure: unknown) => failure)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 409, code: 'VIDEO_NOT_READY', correlationId: 'corr-1', message: 'Não pronto' })
    expect(console.error).toHaveBeenCalledWith('Falha na API', expect.objectContaining({ correlationId: 'corr-1' }))
  })

  it('não trata um corpo inválido como sucesso', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    server.use(http.get(`${API}/eco`, () => new HttpResponse('<html>erro</html>', { status: 502 })))

    await expect(apiRequest('/eco')).rejects.toMatchObject({ status: 502, body: undefined })
  })

  it('identifica falhas de rede com status 0', async () => {
    server.use(http.get(`${API}/eco`, () => HttpResponse.error()))

    await expect(apiRequest('/eco')).rejects.toMatchObject({ status: 0, code: 'NETWORK_ERROR' })
  })

  it('devolve undefined em 204 e avisa sobre sessão expirada em 401', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    server.use(
      http.delete(`${API}/eco`, () => new HttpResponse(null, { status: 204 })),
      http.get(`${API}/eco`, () => HttpResponse.json({ code: 'UNAUTHORIZED', message: 'x', correlation_id: 'c' }, { status: 401 })),
    )

    await expect(apiRequest('/eco', { method: 'DELETE' })).resolves.toBeUndefined()
    await expect(apiRequest('/eco')).rejects.toMatchObject({ status: 401 })
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })
})

describe('createJob', () => {
  it('envia a Idempotency-Key e as operações', async () => {
    let request: { key: string | null; body: unknown } | undefined
    server.use(
      http.post(`${API}/videos/:videoId/jobs`, async ({ request: incoming }) => {
        request = { key: incoming.headers.get('idempotency-key'), body: await incoming.json() }
        return HttpResponse.json({ id: 'job' }, { status: 202 })
      }),
    )

    await createJob('video-1', ['transcription', 'summary'], 'chave-idempotente-0001')
    expect(request).toEqual({ key: 'chave-idempotente-0001', body: { operations: ['transcription', 'summary'] } })
  })
})

class FakeXhr {
  static last: FakeXhr
  method = ''
  url = ''
  headers: Record<string, string> = {}
  body: unknown
  status = 0
  upload: { onprogress?: (event: { lengthComputable: boolean; loaded: number; total: number }) => void } = {}
  onload?: () => void
  onerror?: () => void
  onabort?: () => void

  constructor() {
    FakeXhr.last = this
  }
  open(method: string, url: string) {
    this.method = method
    this.url = url
  }
  setRequestHeader(name: string, value: string) {
    this.headers[name] = value
  }
  send(body: unknown) {
    this.body = body
  }
  abort() {
    this.onabort?.()
  }
}

describe('uploadToSignedUrl', () => {
  const signedUrl = {
    url: 'http://storage.test/videos/v/original.mp4?X-Amz-Signature=abc',
    method: 'PUT' as const,
    expires_at: '2026-10-19T15:00:00Z',
    headers: { 'Content-Type': 'video/mp4' },
  }
  const file = new File(['conteudo'], 'aula.mp4', { type: 'video/mp4' })

  it('envia o arquivo direto para a URL assinada com os headers e informa o progresso', async () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr)
    const progress: number[] = []
    const upload = uploadToSignedUrl(signedUrl, file, (value) => progress.push(value))
    const xhr = FakeXhr.last

    expect(xhr.method).toBe('PUT')
    expect(xhr.url).toBe(signedUrl.url)
    expect(xhr.headers).toEqual({ 'Content-Type': 'video/mp4' })
    expect(xhr.body).toBe(file)

    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 1, total: 4 })
    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 4, total: 4 })
    xhr.status = 200
    xhr.onload?.()

    await expect(upload).resolves.toBeUndefined()
    expect(progress).toEqual([25, 100])
    vi.unstubAllGlobals()
  })

  it('explica URL expirada, rejeição e falha de rede', async () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr)

    const expired = uploadToSignedUrl(signedUrl, file, () => {})
    FakeXhr.last.status = 403
    FakeXhr.last.onload?.()
    await expect(expired).rejects.toMatchObject({ status: 403, message: expect.stringMatching(/expirou/) })

    const rejected = uploadToSignedUrl(signedUrl, file, () => {})
    FakeXhr.last.status = 500
    FakeXhr.last.onload?.()
    await expect(rejected).rejects.toBeInstanceOf(UploadError)

    const offline = uploadToSignedUrl(signedUrl, file, () => {})
    FakeXhr.last.onerror?.()
    await expect(offline).rejects.toMatchObject({ status: 0 })

    const controller = new AbortController()
    const cancelled = uploadToSignedUrl(signedUrl, file, () => {}, controller.signal)
    controller.abort()
    await expect(cancelled).rejects.toMatchObject({ name: 'AbortError' })
    vi.unstubAllGlobals()
  })
})
