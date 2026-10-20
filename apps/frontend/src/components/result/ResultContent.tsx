import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded'
import { Box, Button, Typography } from '@mui/material'
import { brand } from '../../app/theme'
import type { Chapter } from '../../types/result'
import { formatTimestamp } from '../../utils/formatTimestamp'
import { Panel } from '../common/Panel'
import { ChapterBlocks } from './blocks/ChapterBlocks'
import { MarkdownText } from './MarkdownText'

export function SummaryCard({ summary }: { summary: string }) {
  return (
    <Panel title="Resumo" titleId="summary-title" accent="blue" sx={{ p: { xs: 2.5, md: 4 } }}>
      <Box sx={{ fontSize: '1.05rem', color: brand.ink, '& > :last-child': { mb: 0 } }}>
        <MarkdownText>{summary}</MarkdownText>
      </Box>
    </Panel>
  )
}

interface ChapterArticleProps {
  chapter: Chapter
  number: number
  playing: boolean
  onSeek: (seconds: number) => void
}

export function ChapterArticle({ chapter, number, playing, onSeek }: ChapterArticleProps) {
  const titleId = `chapter-${number}`
  return (
    <Box component="article" aria-labelledby={titleId} sx={{ scrollMarginTop: 96 }} id={`capitulo-${number}`}>
      <Typography id={titleId} variant="h2" sx={{ fontSize: { xs: '1.35rem', md: '1.6rem' }, letterSpacing: '-0.02em', mb: 1.25 }}>
        {chapter.title}
      </Typography>
      <Button
        variant={playing ? 'contained' : 'outlined'}
        color={playing ? 'secondary' : 'primary'}
        size="small"
        startIcon={<PlayArrowRoundedIcon />}
        onClick={() => onSeek(chapter.start_seconds)}
        aria-label={`Assistir o capítulo ${number}, de ${formatTimestamp(chapter.start_seconds)} a ${formatTimestamp(chapter.end_seconds)}`}
        sx={{ mb: 2.5 }}
      >
        Capítulo {number} · {formatTimestamp(chapter.start_seconds)} – {formatTimestamp(chapter.end_seconds)}
      </Button>
      {chapter.blocks && chapter.blocks.length > 0 && <ChapterBlocks blocks={chapter.blocks} />}
    </Box>
  )
}
