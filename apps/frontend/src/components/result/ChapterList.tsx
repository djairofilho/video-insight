import { Box, ButtonBase, Stack } from '@mui/material'
import { brand } from '../../app/theme'
import type { Chapter } from '../../types/result'
import { formatTimestamp } from '../../utils/formatTimestamp'

interface ChapterListProps {
  chapters: Chapter[]
  activeIndex: number
  onSeek: (seconds: number) => void
}

export function ChapterList({ chapters, activeIndex, onSeek }: ChapterListProps) {
  return (
    <Stack component="ol" aria-label="Capítulos" sx={{ listStyle: 'none', p: 0, m: 0 }}>
      {chapters.map((chapter, index) => {
        const active = index === activeIndex
        return (
          <li key={`${chapter.start_seconds}-${index}`}>
            <ButtonBase
              onClick={() => onSeek(chapter.start_seconds)}
              aria-current={active ? 'true' : undefined}
              aria-label={`Ir para ${formatTimestamp(chapter.start_seconds)}: ${chapter.title}`}
              sx={{
                width: '100%',
                justifyContent: 'flex-start',
                alignItems: 'baseline',
                textAlign: 'left',
                gap: 1.5,
                px: 1,
                py: 0.75,
                mx: -1,
                borderRadius: '10px',
                bgcolor: active ? brand.blueTint : 'transparent',
                '&:hover': { bgcolor: active ? brand.blueTint : 'action.hover' },
                '&.Mui-focusVisible': { outline: `2px solid ${brand.blue}` },
              }}
            >
              <Box component="span" sx={{ color: active ? brand.blueInk : brand.faint, fontSize: '0.875rem', fontWeight: 600, flexShrink: 0, minWidth: 40 }}>
                {formatTimestamp(chapter.start_seconds)}
              </Box>
              <Box component="span" sx={{ fontWeight: active ? 650 : 500, fontSize: '0.95rem', lineHeight: 1.45, color: active ? brand.blueInk : brand.ink }}>
                {chapter.title}
              </Box>
            </ButtonBase>
          </li>
        )
      })}
    </Stack>
  )
}
