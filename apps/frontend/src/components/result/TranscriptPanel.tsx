import { Alert, Box, Button, ButtonBase, Stack, Typography } from '@mui/material'
import { brand } from '../../app/theme'
import { useEffect, useRef, useState } from 'react'
import { exportTranscript } from '../../services/jobService'
import type { TranscriptFormat, TranscriptSegment } from '../../types/result'
import { describeError } from '../../utils/errorMessages'
import { formatTimestamp } from '../../utils/formatTimestamp'
import { Panel } from '../common/Panel'

const FORMATS: TranscriptFormat[] = ['txt', 'srt', 'json']

interface TranscriptPanelProps {
  jobId: string
  segments: TranscriptSegment[]
  activeIndex: number
  onSeek: (seconds: number) => void
}

export function TranscriptPanel({ jobId, segments, activeIndex, onSeek }: TranscriptPanelProps) {
  const listRef = useRef<HTMLOListElement>(null)

  // Mantém o trecho em reprodução visível rolando só a lista, sem mover a página.
  useEffect(() => {
    const list = listRef.current
    const item = activeIndex >= 0 ? list?.children.item(activeIndex) : null
    if (!list || !(item instanceof HTMLElement)) return
    const top = item.offsetTop - list.offsetTop
    if (top < list.scrollTop || top + item.offsetHeight > list.scrollTop + list.clientHeight) {
      list.scrollTo({ top: top - list.clientHeight / 3, behavior: 'smooth' })
    }
  }, [activeIndex])

  return (
    <Panel
      title="Transcrição"
      titleId="transcript-title"
      actions={<ExportButtons jobId={jobId} />}
      sx={{ display: 'flex', flexDirection: 'column', flex: { md: '1 1 0' }, minHeight: { md: 220 } }}
    >
      {segments.length === 0 ? (
        <Typography sx={{ color: brand.muted }}>Nenhuma fala foi detectada neste vídeo.</Typography>
      ) : (
        <Box
          component="ol"
          ref={listRef}
          tabIndex={0}
          aria-label="Trechos da transcrição"
          sx={{ listStyle: 'none', p: 0, m: 0, maxHeight: { xs: 360, md: 'none' }, flex: { md: '1 1 0' }, minHeight: 0, overflowY: 'auto', overscrollBehavior: 'contain' }}
        >
          {segments.map((segment, index) => {
            const active = index === activeIndex
            return (
              <li key={`${segment.start_seconds}-${index}`}>
                <ButtonBase
                  onClick={() => onSeek(segment.start_seconds)}
                  aria-current={active ? 'true' : undefined}
                  sx={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    alignItems: 'flex-start',
                    textAlign: 'left',
                    gap: 1.5,
                    px: 1,
                    py: 0.75,
                    borderRadius: '10px',
                    bgcolor: active ? brand.blueTint : 'transparent',
                    '&:hover': { bgcolor: active ? brand.blueTint : 'action.hover' },
                    '&.Mui-focusVisible': { outline: `2px solid ${brand.blue}` },
                  }}
                >
                  <Box component="span" sx={{ color: active ? brand.blueInk : brand.faint, fontSize: '0.8125rem', fontWeight: 600, pt: 0.25, flexShrink: 0, minWidth: 40 }}>
                    {formatTimestamp(segment.start_seconds)}
                  </Box>
                  <Box component="span" sx={{ fontSize: '0.95rem', lineHeight: 1.55, color: brand.ink }}>
                    {segment.text}
                  </Box>
                </ButtonBase>
              </li>
            )
          })}
        </Box>
      )}
    </Panel>
  )
}

/** Cada clique pede uma URL nova ao Job Service, então uma URL expirada nunca é reutilizada. */
function ExportButtons({ jobId }: { jobId: string }) {
  const [busy, setBusy] = useState<TranscriptFormat | null>(null)
  const [error, setError] = useState<unknown>(null)

  const download = async (format: TranscriptFormat) => {
    setBusy(format)
    setError(null)
    try {
      const { url } = await exportTranscript(jobId, format)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.rel = 'noopener'
      anchor.click()
    } catch (failure) {
      setError(failure)
    } finally {
      setBusy(null)
    }
  }

  return (
    <Box>
      <Stack direction="row" spacing={0.75} role="group" aria-label="Exportar transcrição">
        {FORMATS.map((format) => (
          <Button
            key={format}
            size="small"
            variant="outlined"
            loading={busy === format}
            disabled={busy !== null && busy !== format}
            onClick={() => void download(format)}
            aria-label={`Baixar transcrição em ${format.toUpperCase()}`}
            sx={{ minWidth: 0, px: 1.25, py: 0.25, fontSize: '0.8rem' }}
          >
            {format.toUpperCase()}
          </Button>
        ))}
      </Stack>
      {error !== null && (
        <Alert severity="error" sx={{ mt: 1 }} onClose={() => setError(null)}>
          {describeError(error)}
        </Alert>
      )}
    </Box>
  )
}
