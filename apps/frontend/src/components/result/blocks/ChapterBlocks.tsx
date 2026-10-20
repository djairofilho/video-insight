import { Box, Paper, Typography } from '@mui/material'
import { brand } from '../../../app/theme'
import type { CalloutBlock, CalloutVariant, ChapterBlock } from '../../../types/result'
import { asKnownBlock } from '../../../utils/blocks'
import { MarkdownText } from '../MarkdownText'
import { ComparisonDiagram, CycleDiagram, FlowDiagram, TreeDiagram } from './Diagrams'

// Cada tipo de destaque com um tom claro e um texto escuro do mesmo tom (contraste de pelo menos 4,5:1).
const CALLOUTS: Record<CalloutVariant, { label: string; fill: string; accent: string; ink: string }> = {
  definition: { label: 'Definição', fill: brand.blueTint, accent: brand.blue, ink: brand.blueInk },
  important: { label: 'Importante', fill: '#fdf3e1', accent: '#d4952b', ink: '#7a4a00' },
  curiosity: { label: 'Curiosidade', fill: brand.tealTint, accent: brand.teal, ink: brand.tealInk },
  warning: { label: 'Atenção', fill: brand.negativeTint, accent: brand.negative, ink: brand.negativeInk },
  reflection: { label: 'Para refletir', fill: brand.raised, accent: brand.faint, ink: brand.muted },
}

function Callout({ block }: { block: CalloutBlock }) {
  const style = CALLOUTS[block.variant]
  return (
    <Paper component="aside" sx={{ my: 3, p: { xs: 2, md: 2.5 }, bgcolor: style.fill, borderLeft: `4px solid ${style.accent}`, borderRadius: '12px' }}>
      <Typography variant="body2" component="p" sx={{ color: style.ink, fontWeight: 650 }}>
        {style.label}
      </Typography>
      <Typography variant="h4" component="p" sx={{ mb: 0.5, color: brand.ink }}>
        {block.title}
      </Typography>
      <Typography sx={{ color: brand.ink }}>
        <MarkdownText inline>{block.text}</MarkdownText>
      </Typography>
    </Paper>
  )
}

function Block({ block }: { block: ChapterBlock }) {
  const known = asKnownBlock(block)
  if (!known) {
    return (
      <Typography variant="body2" sx={{ my: 2, color: 'text.secondary', fontStyle: 'italic' }}>
        Conteúdo indisponível nesta versão.
      </Typography>
    )
  }
  switch (known.type) {
    case 'paragraph':
      return (
        <Typography component="div" sx={{ mb: 2, color: brand.ink, '& strong': { fontWeight: 700 } }}>
          <MarkdownText inline>{known.text}</MarkdownText>
        </Typography>
      )
    case 'callout':
      return <Callout block={known} />
    case 'flow':
      return <FlowDiagram block={known} />
    case 'cycle':
      return <CycleDiagram block={known} />
    case 'comparison':
      return <ComparisonDiagram block={known} />
    case 'tree':
      return <TreeDiagram block={known} />
  }
}

export function ChapterBlocks({ blocks }: { blocks: ChapterBlock[] }) {
  return (
    <Box>
      {blocks.map((block, index) => (
        <Block key={index} block={block} />
      ))}
    </Box>
  )
}
