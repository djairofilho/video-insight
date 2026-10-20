import type { CursorPage } from './api'

export type UploadStatus = 'pending' | 'uploading' | 'ready' | 'failed'

/** Schema `Video` de `contracts/openapi/video-service.yaml`. */
export interface Video {
  id: string
  file_name: string
  content_type: string
  size_bytes: number
  duration_seconds?: number
  upload_status: UploadStatus
  created_at: string
  updated_at?: string
}

export type VideoPage = CursorPage<Video>

export interface CreateVideoRequest {
  file_name: string
  content_type: 'video/mp4'
  size_bytes: number
}
