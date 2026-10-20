import ArrowDownwardRoundedIcon from '@mui/icons-material/ArrowDownwardRounded'
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded'
import LoopRoundedIcon from '@mui/icons-material/LoopRounded'
import { Box, Stack, Typography, useMediaQuery, useTheme } from '@mui/material'
import { Fragment } from 'react'
import type { ComparisonBlock, CycleBlock, FlowBlock, TreeBlock } from '../../../types/result'
import { diagramColor } from './diagramColors'
import { DiagramFrame, DiagramNode } from './DiagramFrame'

export function FlowDiagram({ block }: { block: FlowBlock }) {
  const theme = useTheme()
  const vertical = useMediaQuery(theme.breakpoints.down('sm'))
  const Arrow = vertical ? ArrowDownwardRoundedIcon : ArrowForwardRoundedIcon
  return (
    <DiagramFrame title={block.title}>
      <Stack
        component="ol"
        direction={vertical ? 'column' : 'row'}
        sx={{ listStyle: 'none', p: 0, m: 0, alignItems: 'stretch', gap: 1 }}
      >
        {block.steps.map((step, index) => (
          <Fragment key={`${step.label}-${index}`}>
            {index > 0 && (
              <Box aria-hidden sx={{ display: 'grid', placeItems: 'center', color: 'text.secondary' }}>
                <Arrow fontSize="small" />
              </Box>
            )}
            <Box component="li" sx={{ flex: 1, minWidth: 0, display: 'grid' }}>
              <DiagramNode index={index} detail={step.detail}>
                {step.label}
              </DiagramNode>
            </Box>
          </Fragment>
        ))}
      </Stack>
    </DiagramFrame>
  )
}

export function CycleDiagram({ block }: { block: CycleBlock }) {
  const theme = useTheme()
  const narrow = useMediaQuery(theme.breakpoints.down('sm'))
  const count = block.stages.length

  if (narrow) {
    return (
      <DiagramFrame title={block.title}>
        <Stack component="ol" spacing={1} sx={{ listStyle: 'none', p: 0, m: 0 }}>
          {block.stages.map((stage, index) => (
            <li key={`${stage}-${index}`}>
              <DiagramNode index={index}>{stage}</DiagramNode>
            </li>
          ))}
        </Stack>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center', justifyContent: 'center', mt: 1.5, color: 'text.secondary' }}>
          <LoopRoundedIcon fontSize="small" />
          <Typography variant="body2">{block.center ?? 'Recomeça na primeira etapa'}</Typography>
        </Stack>
      </DiagramFrame>
    )
  }

  // Etapas distribuídas num círculo a partir do topo, no sentido horário.
  const radius = 36
  const position = (index: number) => {
    const angle = (-90 + (360 * index) / count) * (Math.PI / 180)
    return { x: 50 + radius * Math.cos(angle), y: 50 + radius * Math.sin(angle), angle }
  }
  const gap = Math.min(28, 120 / count) * (Math.PI / 180)
  const arcs = block.stages.map((_, index) => {
    const from = position(index).angle + gap
    const to = position(index + 1).angle - gap
    const start = { x: 50 + radius * Math.cos(from), y: 50 + radius * Math.sin(from) }
    const end = { x: 50 + radius * Math.cos(to), y: 50 + radius * Math.sin(to) }
    return `M ${start.x} ${start.y} A ${radius} ${radius} 0 0 1 ${end.x} ${end.y}`
  })

  return (
    <DiagramFrame title={block.title}>
      <Box sx={{ position: 'relative', width: '100%', maxWidth: 520, mx: 'auto', aspectRatio: '1 / 1' }}>
        <Box component="svg" viewBox="0 0 100 100" aria-hidden sx={{ position: 'absolute', inset: 0, color: 'text.secondary' }}>
          <defs>
            <marker id="cycle-arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" />
            </marker>
          </defs>
          {arcs.map((path) => (
            <path key={path} d={path} fill="none" stroke="currentColor" strokeWidth="0.6" markerEnd="url(#cycle-arrow)" />
          ))}
        </Box>
        <Box component="ol" sx={{ listStyle: 'none', p: 0, m: 0 }}>
          {block.stages.map((stage, index) => {
            const { x, y } = position(index)
            return (
              <Box
                component="li"
                key={`${stage}-${index}`}
                sx={{ position: 'absolute', left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)', width: '30%' }}
              >
                <DiagramNode index={index}>{stage}</DiagramNode>
              </Box>
            )
          })}
        </Box>
        <Stack
          sx={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
            width: '34%',
            alignItems: 'center',
            textAlign: 'center',
            color: 'text.secondary',
          }}
        >
          <LoopRoundedIcon fontSize="small" />
          {block.center && <Typography variant="body2" sx={{ fontWeight: 600 }}>{block.center}</Typography>}
        </Stack>
      </Box>
    </DiagramFrame>
  )
}

export function ComparisonDiagram({ block }: { block: ComparisonBlock }) {
  const [left, right] = block.columns
  const rows = Math.max(left.items.length, right.items.length)
  return (
    <DiagramFrame title={block.title}>
      <Box
        role="table"
        aria-label={block.title}
        sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}
      >
        <Box role="row" sx={{ display: 'contents' }}>
          {[left, right].map((column, index) => (
            <Box
              role="columnheader"
              key={column.heading}
              sx={{
                bgcolor: diagramColor(index).fill,
                borderTop: `3px solid ${diagramColor(index).border}`,
                borderRadius: '10px',
                px: 1.5,
                py: 1,
                textAlign: 'center',
                fontWeight: 650,
              }}
            >
              {column.heading}
            </Box>
          ))}
        </Box>
        {Array.from({ length: rows }, (_, row) => (
          <Box role="row" key={row} sx={{ display: 'contents' }}>
            {[left, right].map((column, index) => (
              <Box
                role="cell"
                key={index}
                sx={{ bgcolor: 'background.paper', borderRadius: '10px', px: 1.5, py: 1, textAlign: 'center' }}
              >
                {column.items[row] ?? '—'}
              </Box>
            ))}
          </Box>
        ))}
      </Box>
      {block.shared && (
        <Typography sx={{ mt: 2, textAlign: 'center', color: 'text.secondary' }}>
          <Box component="span" sx={{ fontWeight: 650, color: 'text.primary' }}>Em comum: </Box>
          {block.shared}
        </Typography>
      )}
    </DiagramFrame>
  )
}

export function TreeDiagram({ block }: { block: TreeBlock }) {
  return (
    <DiagramFrame title={block.title}>
      <Box sx={{ maxWidth: 260, mx: 'auto' }}>
        <DiagramNode index={3}>{block.root}</DiagramNode>
      </Box>
      <Box aria-hidden sx={{ width: 2, height: 20, bgcolor: 'divider', mx: 'auto' }} />
      <Box
        component="ul"
        sx={{
          listStyle: 'none',
          p: 0,
          m: 0,
          display: 'grid',
          gap: 1.5,
          gridTemplateColumns: { xs: '1fr', sm: `repeat(${Math.min(block.branches.length, 3)}, 1fr)`, md: `repeat(${block.branches.length}, 1fr)` },
          borderTop: { sm: 2 },
          borderColor: { sm: 'divider' },
          pt: { sm: 2 },
        }}
      >
        {block.branches.map((branch, index) => (
          <Box component="li" key={`${branch.label}-${index}`}>
            <DiagramNode index={index}>{branch.label}</DiagramNode>
            {branch.children.length > 0 && (
              <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0, mt: 1, display: 'grid', gap: 0.75 }}>
                {branch.children.map((child) => (
                  <Typography
                    component="li"
                    variant="body2"
                    key={child}
                    sx={{ bgcolor: 'background.paper', borderRadius: '8px', px: 1, py: 0.75, textAlign: 'center' }}
                  >
                    {child}
                  </Typography>
                ))}
              </Box>
            )}
          </Box>
        ))}
      </Box>
    </DiagramFrame>
  )
}
