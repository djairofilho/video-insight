import type { SignedUrl } from '../types/api'
import type { CreateVideoRequest, Video, VideoPage } from '../types/video'
import { apiRequest } from './apiClient'

export function listVideos(cursor?: string, limit = 20, signal?: AbortSignal): Promise<VideoPage> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (cursor) {
    params.set('cursor', cursor)
  }
  return apiRequest<VideoPage>(`/videos?${params}`, { signal })
}

export function getVideo(videoId: string, signal?: AbortSignal): Promise<Video> {
  return apiRequest<Video>(`/videos/${videoId}`, { signal })
}

export function createVideo(request: CreateVideoRequest): Promise<Video> {
  return apiRequest<Video>('/videos', { method: 'POST', json: request })
}

export function deleteVideo(videoId: string): Promise<void> {
  return apiRequest<void>(`/videos/${videoId}`, { method: 'DELETE' })
}

export function createUploadUrl(videoId: string): Promise<SignedUrl> {
  return apiRequest<SignedUrl>(`/videos/${videoId}/upload-url`, { method: 'POST' })
}

export function completeUpload(videoId: string, durationSeconds: number): Promise<Video> {
  return apiRequest<Video>(`/videos/${videoId}/upload-complete`, {
    method: 'POST',
    json: { duration_seconds: durationSeconds },
  })
}

export function createPlaybackUrl(videoId: string): Promise<SignedUrl> {
  return apiRequest<SignedUrl>(`/videos/${videoId}/playback-url`, { method: 'POST' })
}

export class UploadError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'UploadError'
    this.status = status
  }
}

/**
 * Envia o arquivo direto para o armazenamento pela URL assinada, sem passar pelo Gateway. Usa XMLHttpRequest porque
 * `fetch` não informa o progresso do upload. Os headers devolvidos fazem parte da assinatura e precisam ser enviados.
 */
export function uploadToSignedUrl(
  signedUrl: SignedUrl,
  file: File,
  onProgress: (percentage: number) => void,
  signal?: AbortSignal,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open(signedUrl.method, signedUrl.url)
    for (const [name, value] of Object.entries(signedUrl.headers ?? {})) {
      request.setRequestHeader(name, value)
    }

    request.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        resolve()
      } else if (request.status === 403) {
        reject(new UploadError('A autorização de envio expirou. Tente novamente.', request.status))
      } else {
        reject(new UploadError('O armazenamento rejeitou o upload.', request.status))
      }
    }
    request.onerror = () => reject(new UploadError('Falha de rede durante o upload.', 0))
    request.onabort = () => reject(new DOMException('Upload cancelado.', 'AbortError'))
    signal?.addEventListener('abort', () => request.abort(), { once: true })
    request.send(file)
  })
}
