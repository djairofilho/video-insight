/** Schema `Error` dos contratos OpenAPI. */
export interface ApiErrorBody {
  code: string
  message: string
  correlation_id: string
}

/** Schema `SignedUrl` do Video Service. */
export interface SignedUrl {
  url: string
  method: 'GET' | 'PUT'
  expires_at: string
  headers?: Record<string, string>
}

/** Schema `ExportUrl` do Job Service. */
export interface ExportUrl {
  url: string
  expires_at: string
}

/** Página com cursor opaco, usada por `VideoPage` e `JobPage`. */
export interface CursorPage<T> {
  items: T[]
  next_cursor?: string
}
