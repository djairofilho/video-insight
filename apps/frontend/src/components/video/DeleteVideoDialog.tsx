import { Alert } from '@mui/material'
import { useState } from 'react'
import { deleteVideo } from '../../services/videoService'
import type { Video } from '../../types/video'
import { describeError } from '../../utils/errorMessages'
import { ConfirmDialog } from '../common/ConfirmDialog'

interface DeleteVideoDialogProps {
  video: Video | null
  onClose: () => void
  onDeleted: (video: Video) => void
}

export function DeleteVideoDialog({ video, onClose, onDeleted }: DeleteVideoDialogProps) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const close = () => {
    setError(null)
    onClose()
  }

  const confirm = async () => {
    if (!video) return
    setBusy(true)
    setError(null)
    try {
      await deleteVideo(video.id)
      onDeleted(video)
    } catch (failure) {
      setError(failure)
    } finally {
      setBusy(false)
    }
  }

  return (
    <ConfirmDialog
      open={video !== null}
      title="Excluir vídeo?"
      description={
        <>
          O arquivo <strong>{video?.file_name}</strong> será apagado do armazenamento. Essa ação não pode ser desfeita.
          {error !== null && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {describeError(error)}
            </Alert>
          )}
        </>
      }
      confirmLabel="Excluir"
      destructive
      busy={busy}
      onConfirm={() => void confirm()}
      onClose={close}
    />
  )
}
