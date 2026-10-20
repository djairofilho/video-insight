export const MAX_VIDEO_BYTES = 104_857_600
export const MAX_VIDEO_SECONDS = 600
export const VIDEO_CONTENT_TYPE = 'video/mp4'

/**
 * Validações do MVP feitas antes de chamar a API. Melhoram a experiência, mas não substituem as do Video Service.
 * Devolve a mensagem de erro, ou `null` quando o arquivo é aceito.
 */
export function validateVideoFile(file: File): string | null {
  if (file.type !== VIDEO_CONTENT_TYPE) {
    return 'Envie um arquivo no formato MP4.'
  }
  if (file.size === 0) {
    return 'O arquivo está vazio.'
  }
  if (file.size > MAX_VIDEO_BYTES) {
    return 'O arquivo passa do limite de 100 MB.'
  }
  return null
}

export function validateVideoDuration(seconds: number): string | null {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return 'Não foi possível ler a duração do vídeo. Verifique se o arquivo não está corrompido.'
  }
  if (seconds > MAX_VIDEO_SECONDS) {
    return 'O vídeo passa do limite de 10 minutos.'
  }
  return null
}

/** Lê a duração com um elemento `<video>`, sem enviar nada para a rede. */
export function readVideoDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const video = document.createElement('video')
    video.preload = 'metadata'
    const cleanup = () => {
      URL.revokeObjectURL(url)
      video.removeAttribute('src')
    }
    video.onloadedmetadata = () => {
      const duration = video.duration
      cleanup()
      resolve(duration)
    }
    video.onerror = () => {
      cleanup()
      reject(new Error('Não foi possível ler o vídeo.'))
    }
    video.src = url
  })
}
