import { Box, Paper, Typography } from '@mui/material'
import { useId, type ReactNode } from 'react'
import { diagramColor } from './diagramColors'

export function DiagramFrame({ title, children }: { title: string; children: ReactNode }) {
  const captionId = useId()
  return (
    <Paper component="figure" aria-labelledby={captionId} sx={{ m: 0, my: 3, p: { xs: 2, md: 3 }, bgcolor: '#f8fafd', borderRadius: '12px' }}>
      <Typography id={captionId} component="figcaption" variant="h4" sx={{ textAlign: 'center', mb: 2.5 }}>
        {title}
      </Typography>
      {children}
    </Paper>
  )
}

interface DiagramNodeProps {
  index: number
  children: ReactNode
  detail?: ReactNode
}

export function DiagramNode({ index, children, detail }: DiagramNodeProps) {
  const color = diagramColor(index)
  return (
    <Box
      sx={{
        // Faixa de cor no topo, como os cartões da marca, em vez de contorno grosso.
        borderTop: `3px solid ${color.border}`,
        bgcolor: color.fill,
        borderRadius: '10px',
        px: 1.5,
        py: 1.25,
        textAlign: 'center',
        minWidth: 0,
      }}
    >
      <Typography sx={{ fontWeight: 600, lineHeight: 1.3, overflowWrap: 'anywhere' }}>{children}</Typography>
      {detail && (
        <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5, lineHeight: 1.4 }}>
          {detail}
        </Typography>
      )}
    </Box>
  )
}
