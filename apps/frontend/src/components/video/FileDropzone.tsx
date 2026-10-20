import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined'
import { Box, Typography } from '@mui/material'
import { brand } from '../../app/theme'
import { useId, useState, type DragEvent } from 'react'

interface FileDropzoneProps {
  onFile: (file: File) => void
  disabled?: boolean
}

export function FileDropzone({ onFile, disabled = false }: FileDropzoneProps) {
  const inputId = useId()
  const [dragging, setDragging] = useState(false)

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault()
    setDragging(false)
    const file = event.dataTransfer.files.item(0)
    if (file && !disabled) {
      onFile(file)
    }
  }

  return (
    <Box
      component="label"
      htmlFor={inputId}
      onDragOver={(event: DragEvent<HTMLLabelElement>) => {
        event.preventDefault()
        if (!disabled) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 1,
        px: 3,
        py: { xs: 6, md: 8 },
        minHeight: { md: 400 },
        border: 2,
        borderStyle: 'dashed',
        borderColor: dragging ? brand.blue : brand.control,
        borderRadius: '12px',
        bgcolor: dragging ? brand.blueTint : brand.surface,
        textAlign: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
        transition: 'border-color 150ms, background-color 150ms',
        '&:hover': disabled ? undefined : { borderColor: brand.blue },
        '&:focus-within': { outline: `2px solid ${brand.blue}`, outlineOffset: 2 },
      }}
    >
      <CloudUploadOutlinedIcon sx={{ fontSize: 40, color: brand.blue }} />
      <Typography variant="h2" component="span">
        Arraste o vídeo aqui ou clique para escolher
      </Typography>
      <Typography sx={{ color: brand.muted }}>MP4 de até 100 MB e até 10 minutos</Typography>
      <input
        id={inputId}
        type="file"
        accept="video/mp4"
        disabled={disabled}
        onChange={(event) => {
          const file = event.target.files?.item(0)
          event.target.value = ''
          if (file) onFile(file)
        }}
        style={{ position: 'absolute', width: 1, height: 1, opacity: 0, overflow: 'hidden' }}
      />
    </Box>
  )
}
