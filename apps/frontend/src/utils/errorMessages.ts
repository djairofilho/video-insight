import { ApiError } from '../services/apiClient'
import { UploadError } from '../services/videoService'

/** Mensagens para os códigos de erro dos serviços. Códigos desconhecidos usam a mensagem da própria API. */
const MESSAGES: Record<string, string> = {
  NETWORK_ERROR: 'Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.',
  VIDEO_NOT_FOUND: 'Vídeo não encontrado.',
  JOB_NOT_FOUND: 'Processamento não encontrado.',
  VIDEO_NOT_READY: 'O envio do vídeo ainda não foi confirmado.',
  UPLOAD_NOT_FOUND: 'O arquivo não chegou ao armazenamento. Envie o vídeo novamente.',
  UPLOAD_SIZE_MISMATCH: 'O arquivo recebido tem um tamanho diferente do informado. Cadastre o vídeo de novo.',
  IDEMPOTENCY_KEY_REUSED: 'Este pedido já foi enviado com outras opções. Tente novamente.',
  INVALID_JOB_STATE: 'O processamento mudou de estado. Atualize a página.',
  JOB_NOT_COMPLETED: 'O resultado ainda não está disponível.',
  ARTIFACT_NOT_AVAILABLE: 'Este formato não está disponível para este processamento.',
  VIDEO_SERVICE_UNAVAILABLE: 'O serviço de vídeos está indisponível no momento. Tente novamente em instantes.',
  INTERNAL_ERROR: 'Ocorreu um erro inesperado no servidor.',
}

export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'Sua sessão expirou. Entre novamente.'
    }
    const known = error.code ? MESSAGES[error.code] : undefined
    return known ?? error.body?.message ?? error.message
  }
  if (error instanceof UploadError) {
    return error.message
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return 'Algo deu errado. Tente novamente.'
}

/** Identificador para o usuário informar ao suporte; os logs também guardam o `correlation_id`. */
export function correlationIdOf(error: unknown): string | undefined {
  return error instanceof ApiError ? error.correlationId : undefined
}

export function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}
