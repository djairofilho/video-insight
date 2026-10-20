import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { API } from '../mocks/handlers'
import { uploadToSignedUrl } from '../services/videoService'
import { renderRoute } from '../test/render'
import { server } from '../test/server'
import { readVideoDuration } from '../utils/validateVideoFile'

// O jsdom não decodifica vídeo nem tem progresso real de upload; a URL assinada é testada em services.test.ts.
vi.mock('../utils/validateVideoFile', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../utils/validateVideoFile')>()),
  readVideoDuration: vi.fn(),
}))
vi.mock('../services/videoService', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../services/videoService')>()),
  uploadToSignedUrl: vi.fn(),
}))

const file = () => new File(['conteudo-do-video'], 'aula.mp4', { type: 'video/mp4' })

beforeEach(() => {
  vi.mocked(readVideoDuration).mockResolvedValue(120.5)
  vi.mocked(uploadToSignedUrl).mockImplementation(async (_url, _file, onProgress) => {
    onProgress(50)
    onProgress(100)
  })
})

describe('Envio de vídeo', () => {
  it('cadastra, envia pela URL assinada, confirma e abre o vídeo', async () => {
    let confirmed: unknown
    server.use(
      http.post(`${API}/videos/:videoId/upload-complete`, async ({ request, params }) => {
        confirmed = await request.json()
        return HttpResponse.json({
          id: params.videoId,
          file_name: 'aula.mp4',
          content_type: 'video/mp4',
          size_bytes: 17,
          duration_seconds: 120.5,
          upload_status: 'ready',
          created_at: '2026-10-19T14:30:00Z',
        })
      }),
    )
    const { router } = renderRoute('/videos/new')

    await userEvent.upload(await screen.findByLabelText(/Arraste o vídeo/), file())

    await waitFor(() => expect(router.state.location.pathname).toMatch(/^\/videos\/[0-9a-f-]{36}$/))
    expect(confirmed).toEqual({ duration_seconds: 120.5 })
    const [signedUrl, sent] = vi.mocked(uploadToSignedUrl).mock.calls[0]
    expect(signedUrl).toMatchObject({ method: 'PUT', headers: { 'Content-Type': 'video/mp4' } })
    expect(sent.name).toBe('aula.mp4')
  })

  it('rejeita arquivos que não são MP4 sem chamar a API', async () => {
    const created = vi.fn()
    server.use(http.post(`${API}/videos`, () => {
      created()
      return HttpResponse.json({}, { status: 201 })
    }))
    renderRoute('/videos/new')

    const user = userEvent.setup({ applyAccept: false })
    await user.upload(await screen.findByLabelText(/Arraste o vídeo/), new File(['x'], 'aula.mov', { type: 'video/quicktime' }))

    expect(await screen.findByText('Arquivo não aceito')).toBeInTheDocument()
    expect(screen.getByText('Envie um arquivo no formato MP4.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Tentar novamente' })).not.toBeInTheDocument()
    expect(created).not.toHaveBeenCalled()
  })

  it('rejeita vídeos com mais de 10 minutos', async () => {
    vi.mocked(readVideoDuration).mockResolvedValue(601)
    renderRoute('/videos/new')
    await userEvent.upload(await screen.findByLabelText(/Arraste o vídeo/), file())
    expect(await screen.findByText('O vídeo passa do limite de 10 minutos.')).toBeInTheDocument()
  })

  it('permite repetir o envio reaproveitando o vídeo cadastrado', async () => {
    let created = 0
    server.use(
      http.post(`${API}/videos`, async ({ request }) => {
        created += 1
        const body = (await request.json()) as { file_name: string; size_bytes: number }
        return HttpResponse.json(
          { id: '11111111-2222-4333-8444-555555555555', ...body, content_type: 'video/mp4', upload_status: 'pending', created_at: '2026-10-19T14:30:00Z' },
          { status: 201 },
        )
      }),
      http.post(`${API}/videos/:videoId/upload-url`, () =>
        HttpResponse.json({ url: 'http://storage.test/x', method: 'PUT', expires_at: '2026-10-19T15:00:00Z' }),
      ),
      http.post(`${API}/videos/:videoId/upload-complete`, ({ params }) =>
        HttpResponse.json({ id: params.videoId, file_name: 'aula.mp4', content_type: 'video/mp4', size_bytes: 17, upload_status: 'ready', created_at: '2026-10-19T14:30:00Z' }),
      ),
    )
    vi.mocked(uploadToSignedUrl).mockRejectedValueOnce(new Error('Falha de rede durante o upload.'))
    const { router } = renderRoute('/videos/new')

    await userEvent.upload(await screen.findByLabelText(/Arraste o vídeo/), file())
    expect(await screen.findByText('O envio falhou')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/videos/11111111-2222-4333-8444-555555555555'))
    expect(created).toBe(1)
  })
})
