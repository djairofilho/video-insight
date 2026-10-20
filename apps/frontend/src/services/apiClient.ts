import type { ApiErrorBody } from '../types/api'
import { getAccessToken, notifyUnauthorized } from './authService'

export const NETWORK_ERROR = 'NETWORK_ERROR'

/** Falha de uma chamada ao Gateway. `status` 0 indica que não houve resposta (rede ou CORS). */
export class ApiError extends Error {
  readonly status: number
  readonly body?: ApiErrorBody

  constructor(message: string, status: number, body?: ApiErrorBody) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }

  get code(): string | undefined {
    return this.status === 0 ? NETWORK_ERROR : this.body?.code
  }

  get correlationId(): string | undefined {
    return this.body?.correlation_id
  }
}

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  /** Serializado como JSON. */
  json?: unknown
}

function baseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { json, headers, ...init } = options
  const requestHeaders = new Headers(headers)
  requestHeaders.set('Accept', 'application/json')
  if (json !== undefined) {
    requestHeaders.set('Content-Type', 'application/json')
  }
  const token = await getAccessToken()
  if (token) {
    requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  let response: Response
  try {
    response = await fetch(`${baseUrl()}${path}`, {
      ...init,
      headers: requestHeaders,
      body: json === undefined ? undefined : JSON.stringify(json),
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    throw new ApiError('Não foi possível conectar ao servidor.', 0)
  }

  if (!response.ok) {
    const body = await readErrorBody(response)
    const failure = new ApiError(body?.message ?? 'Não foi possível concluir a operação.', response.status, body)
    console.error('Falha na API', { path, status: response.status, code: body?.code, correlationId: body?.correlation_id })
    if (response.status === 401) {
      notifyUnauthorized()
    }
    throw failure
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

/** O parsing fica limitado ao corpo do erro: uma resposta sem JSON continua sendo erro. */
async function readErrorBody(response: Response): Promise<ApiErrorBody | undefined> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === 'object' && 'code' in body && 'message' in body) {
      return body as ApiErrorBody
    }
    return undefined
  } catch {
    return undefined
  }
}
