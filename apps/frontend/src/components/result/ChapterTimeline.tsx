import { Box, ButtonBase, Stack, Tooltip, Typography } from '@mui/material'
import { brand } from '../../app/theme'
import type { Chapter } from '../../types/result'
import { formatTimestamp } from '../../utils/formatTimestamp'

interface ChapterTimelineProps {
  chapters: Chapter[]
  duration: number
  currentTime: number
  activeIndex: number
  onSeek: (seconds: number) => void
}

/**
 * Linha do tempo de capítulos: a duração do vídeo dividida nos capítulos, na proporção real de cada um. O capítulo em
 * reprodução fica em azul, a posição atual aparece como um traço e cada trecho leva o player ao seu início.
 */
export function ChapterTimeline({ chapters, duration, currentTime, activeIndex, onSeek }: ChapterTimelineProps) {
  const total = Math.max(duration, chapters.at(-1)?.end_seconds ?? 0, 1)
  const playhead = Math.min(100, Math.max(0, (currentTime / total) * 100))
  const active = activeIndex >= 0 ? chapters[activeIndex] : undefined

  return (
    <Box>
      <Box sx={{ position: 'relative' }}>
        <Stack direction="row" role="group" aria-label="Linha do tempo dos capítulos" sx={{ gap: '3px', height: 40 }}>
          {chapters.map((chapter, index) => {
            const width = ((chapter.end_seconds - chapter.start_seconds) / total) * 100
            const isActive = index === activeIndex
            const label = `Capítulo ${index + 1}: ${chapter.title}, de ${formatTimestamp(chapter.start_seconds)} a ${formatTimestamp(chapter.end_seconds)}`
            return (
              <Tooltip key={`${chapter.start_seconds}-${index}`} title={chapter.title} placement="top" arrow>
                <ButtonBase
                  onClick={() => onSeek(chapter.start_seconds)}
                  aria-label={label}
                  aria-current={isActive ? 'true' : undefined}
                  sx={{
                    flex: `${Math.max(width, 2)} 1 0`,
                    minWidth: 12,
                    justifyContent: 'flex-start',
                    px: 1,
                    borderRadius: index === 0 ? '10px 4px 4px 10px' : index === chapters.length - 1 ? '4px 10px 10px 4px' : '4px',
                    bgcolor: isActive ? brand.blue : brand.blueTint,
                    color: isActive ? '#fff' : brand.blueInk,
                    fontSize: '0.75rem',
                    fontWeight: 650,
                    overflow: 'hidden',
                    whiteSpace: 'nowrap',
                    transition: 'background-color 150ms',
                    '&:hover': { bgcolor: isActive ? brand.blueInk : brand.blueTintStrong },
                    '&.Mui-focusVisible': { outline: `2px solid ${brand.ink}`, outlineOffset: 2 },
                  }}
                >
                  <Box component="span" sx={{ overflow: 'hidden', textOverflow: 'ellipsis' }} aria-hidden>
                    {index + 1}
                  </Box>
                </ButtonBase>
              </Tooltip>
            )
          })}
        </Stack>
        <Box
          aria-hidden
          sx={{
            position: 'absolute',
            top: -4,
            bottom: -4,
            left: `calc(${playhead}% - 1px)`,
            width: 2,
            borderRadius: '2px',
            bgcolor: brand.ink,
            pointerEvents: 'none',
            transition: 'left 250ms linear',
          }}
        />
      </Box>
      <Stack direction="row" spacing={1} sx={{ mt: 1.25, alignItems: 'baseline', justifyContent: 'space-between' }}>
        <Typography variant="body2" sx={{ fontWeight: 600, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} aria-live="polite">
          {active ? `${activeIndex + 1}. ${active.title}` : 'Entre capítulos'}
        </Typography>
        <Typography variant="body2" sx={{ color: brand.muted, flexShrink: 0 }}>
          {formatTimestamp(currentTime)} / {formatTimestamp(total)}
        </Typography>
      </Stack>
    </Box>
  )
}
