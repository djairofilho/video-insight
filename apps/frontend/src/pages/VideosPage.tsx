import AddRoundedIcon from '@mui/icons-material/AddRounded'
import VideoLibraryOutlinedIcon from '@mui/icons-material/VideoLibraryOutlined'
import { Box, Button, Snackbar, Stack } from '@mui/material'
import { useState } from 'react'
import { Link as RouterLink } from 'react-router'
import { PageHeader } from '../components/common/PageHeader'
import { EmptyState, ErrorState } from '../components/common/States'
import { DeleteVideoDialog } from '../components/video/DeleteVideoDialog'
import { VideoList, VideoListSkeleton } from '../components/video/VideoList'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { listVideos } from '../services/videoService'
import type { Video } from '../types/video'

const PAGE_SIZE = 20

interface MorePages {
  items: Video[]
  cursor?: string
  loading: boolean
  error?: unknown
}

export function VideosPage() {
  const firstPage = useAsyncResource('videos', (signal) => listVideos(undefined, PAGE_SIZE, signal))
  const [more, setMore] = useState<MorePages | null>(null)
  const [removed, setRemoved] = useState<string[]>([])
  const [toDelete, setToDelete] = useState<Video | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const reload = () => {
    setMore(null)
    setRemoved([])
    firstPage.reload()
  }

  const { state } = firstPage
  if (state.status === 'loading') {
    return (
      <>
        <Header />
        <VideoListSkeleton />
      </>
    )
  }
  if (state.status === 'error') {
    return (
      <>
        <Header />
        <ErrorState error={state.error} title="Não foi possível carregar seus vídeos" onRetry={reload} />
      </>
    )
  }

  const videos = [...state.data.items, ...(more?.items ?? [])].filter((video) => !removed.includes(video.id))
  const nextCursor = more ? more.cursor : state.data.next_cursor

  const loadMore = async () => {
    if (!nextCursor) return
    const previous = more?.items ?? []
    setMore({ items: previous, cursor: nextCursor, loading: true })
    try {
      const page = await listVideos(nextCursor, PAGE_SIZE)
      setMore({ items: [...previous, ...page.items], cursor: page.next_cursor, loading: false })
    } catch (error) {
      setMore({ items: previous, cursor: nextCursor, loading: false, error })
    }
  }

  return (
    <>
      <Header videos={videos} hasMore={Boolean(nextCursor)} />
      {videos.length === 0 ? (
        <EmptyState
          icon={<VideoLibraryOutlinedIcon />}
          title="Nenhum vídeo por aqui"
          description="Envie um MP4 de até 10 minutos e 100 MB para gerar transcrição, resumo e capítulos."
          action={
            <Button component={RouterLink} to="/videos/new" variant="contained" startIcon={<AddRoundedIcon />}>
              Enviar meu primeiro vídeo
            </Button>
          }
        />
      ) : (
        <Stack spacing={2}>
          <VideoList videos={videos} onDelete={setToDelete} />
          {more?.error !== undefined && (
            <ErrorState error={more.error} title="Não foi possível carregar mais vídeos" onRetry={() => void loadMore()} />
          )}
          {nextCursor && more?.error === undefined && (
            <Box sx={{ textAlign: 'center' }}>
              <Button variant="outlined" onClick={() => void loadMore()} loading={more?.loading ?? false}>
                Carregar mais
              </Button>
            </Box>
          )}
        </Stack>
      )}
      <DeleteVideoDialog
        video={toDelete}
        onClose={() => setToDelete(null)}
        onDeleted={(video) => {
          setRemoved((ids) => [...ids, video.id])
          setToDelete(null)
          setNotice(`“${video.file_name}” foi excluído.`)
        }}
      />
      <Snackbar
        open={notice !== null}
        autoHideDuration={4000}
        onClose={() => setNotice(null)}
        message={notice}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </>
  )
}

function Header({ videos, hasMore = false }: { videos?: Video[]; hasMore?: boolean }) {
  return <PageHeader title="Meus vídeos" description={videos && videos.length > 0 ? summarize(videos, hasMore) : undefined} />
}

/** Uma linha com o que importa na lista: quantos vídeos e quantos estão prontos para processar. */
function summarize(videos: Video[], hasMore: boolean): string {
  const ready = videos.filter((video) => video.upload_status === 'ready').length
  const total = `${videos.length}${hasMore ? '+' : ''} ${videos.length === 1 ? 'vídeo' : 'vídeos'}`
  const readyText = ready === 1 ? '1 pronto para processar' : `${ready} prontos para processar`
  return `${total} · ${readyText}`
}
