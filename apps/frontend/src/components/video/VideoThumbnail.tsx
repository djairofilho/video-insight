import MovieOutlinedIcon from '@mui/icons-material/MovieOutlined'
import { Box } from '@mui/material'
import { useEffect, useState } from 'react'
import { brand } from '../../app/theme'
import { createPlaybackUrl } from '../../services/videoService'
import type { Video } from '../../types/video'

// A URL de reprodução vale 15 minutos; guardamos cada uma por 10 para não pedir de novo a cada visita à lista.
const CACHE_MS = 10 * 60_000
const cache = new Map<string, { url: string; at: number }>()

async function thumbnailUrl(videoId: string): Promise<string> {
  const cached = cache.get(videoId)
  if (cached && Date.now() - cached.at < CACHE_MS) {
    return cached.url
  }
  const { url } = await createPlaybackUrl(videoId)
  cache.set(videoId, { url, at: Date.now() })
  return url
}

interface VideoThumbnailProps {
  video: Video
  width?: number | string
}

/**
 * Miniatura tirada do próprio vídeo: o navegador baixa só os metadados e mostra o quadro de 1 s. Vídeos que ainda não
 * estão prontos, ou sem acesso ao arquivo, mostram um quadro neutro.
 */
export function VideoThumbnail({ video, width = 112 }: VideoThumbnailProps) {
  const ready = video.upload_status === 'ready'
  const [loaded, setLoaded] = useState<{ id: string; url: string | null } | null>(null)

  useEffect(() => {
    if (!ready) return
    let active = true
    thumbnailUrl(video.id).then(
      (url) => active && setLoaded({ id: video.id, url }),
      () => active && setLoaded({ id: video.id, url: null }),
    )
    return () => {
      active = false
    }
  }, [ready, video.id])

  const url = loaded?.id === video.id ? loaded.url : null

  return (
    <Box
      aria-hidden
      sx={{
        width,
        flexShrink: 0,
        aspectRatio: '16 / 9',
        borderRadius: '10px',
        overflow: 'hidden',
        bgcolor: ready ? brand.ink : brand.raised,
        display: 'grid',
        placeItems: 'center',
        color: ready ? '#8d99b8' : brand.faint,
      }}
    >
      {url ? (
        <Box
          component="video"
          src={`${url}#t=1`}
          preload="metadata"
          muted
          playsInline
          tabIndex={-1}
          onError={() => setLoaded({ id: video.id, url: null })}
          sx={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block', pointerEvents: 'none' }}
        />
      ) : (
        <MovieOutlinedIcon fontSize="small" />
      )}
    </Box>
  )
}
