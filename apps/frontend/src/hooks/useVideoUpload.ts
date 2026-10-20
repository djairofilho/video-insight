import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../services/apiClient'
import {
  completeUpload,
  createUploadUrl,
  createVideo,
  uploadToSignedUrl,
} from '../services/videoService'
import type { Video } from '../types/video'
import {
  readVideoDuration,
  validateVideoDuration,
  validateVideoFile,
  VIDEO_CONTENT_TYPE,
} from '../utils/validateVideoFile'

export type UploadPhase = 'idle' | 'validating' | 'creating' | 'uploading' | 'confirming' | 'done' | 'error'

export interface UploadState {
  phase: UploadPhase
  progress: number
  file?: File
  video?: Video
  error?: unknown
  /** Erro de validação local: não há o que repetir, o usuário precisa escolher outro arquivo. */
  rejected?: boolean
}

const INITIAL: UploadState = { phase: 'idle', progress: 0 }

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

/**
 * Sequência de envio: validação local, `POST /videos`, URL assinada, `PUT` direto no armazenamento e confirmação. Ao
 * repetir depois de uma falha, o vídeo já cadastrado é reaproveitado e o envio recomeça a partir da URL assinada.
 */
export function useVideoUpload() {
  const [state, setState] = useState<UploadState>(INITIAL)
  const controllerRef = useRef<AbortController | null>(null)

  useEffect(() => () => controllerRef.current?.abort(), [])

  async function start(file: File, existing?: Video) {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    const update = (patch: Partial<UploadState>) => {
      if (!controller.signal.aborted) {
        setState((previous) => ({ ...previous, ...patch }))
      }
    }

    setState({ phase: 'validating', progress: 0, file, video: existing })
    const fileProblem = validateVideoFile(file)
    if (fileProblem) {
      update({ phase: 'error', error: new Error(fileProblem), rejected: true })
      return
    }

    let video = existing
    try {
      const duration = await readVideoDuration(file).catch(() => Number.NaN)
      const durationProblem = validateVideoDuration(duration)
      if (durationProblem) {
        update({ phase: 'error', error: new Error(durationProblem), rejected: true })
        return
      }

      if (!video) {
        update({ phase: 'creating' })
        video = await createVideo({ file_name: file.name, content_type: VIDEO_CONTENT_TYPE, size_bytes: file.size })
        update({ video })
      }
      const signedUrl = await createUploadUrl(video.id)
      update({ phase: 'uploading', progress: 0 })
      await uploadToSignedUrl(signedUrl, file, (progress) => update({ progress }), controller.signal)
      update({ phase: 'confirming', progress: 100 })
      const ready = await completeUpload(video.id, duration)
      update({ phase: 'done', video: ready })
    } catch (error) {
      if (isAbort(error)) return
      // Com tamanho divergente o Video Service marca o vídeo como `failed`, então a nova tentativa recadastra.
      const sizeMismatch = error instanceof ApiError && error.code === 'UPLOAD_SIZE_MISMATCH'
      update({ phase: 'error', error, video: sizeMismatch ? undefined : video })
    }
  }

  return {
    state,
    start: (file: File) => start(file),
    retry: () => {
      if (state.file) {
        void start(state.file, state.video)
      }
    },
    cancel: () => {
      controllerRef.current?.abort()
      setState(INITIAL)
    },
    reset: () => setState(INITIAL),
  }
}
