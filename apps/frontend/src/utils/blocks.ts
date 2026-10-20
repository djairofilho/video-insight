import type {
  CalloutBlock,
  CalloutVariant,
  ChapterBlock,
  ComparisonBlock,
  CycleBlock,
  FlowBlock,
  KnownBlock,
  ParagraphBlock,
  TreeBlock,
} from '../types/result'

export const CALLOUT_VARIANTS: readonly CalloutVariant[] = ['definition', 'important', 'curiosity', 'warning', 'reflection']

/**
 * Valida o formato mínimo de cada bloco antes de renderizar. O Processing Service pode evoluir; um tipo desconhecido
 * ou incompleto vira "conteúdo indisponível" em vez de quebrar a tela.
 */
export function asKnownBlock(block: ChapterBlock): KnownBlock | null {
  const value: Record<string, unknown> = { ...block }
  const isString = (field: string) => typeof value[field] === 'string'
  const isArray = (field: string) => Array.isArray(value[field])
  switch (block.type) {
    case 'paragraph':
      return isString('text') ? (block as ParagraphBlock) : null
    case 'callout':
      return isString('text') && isString('title') && typeof value.variant === 'string' && CALLOUT_VARIANTS.includes(value.variant as CalloutVariant)
        ? (block as CalloutBlock)
        : null
    case 'flow':
      return isString('title') && isArray('steps') ? (block as FlowBlock) : null
    case 'cycle':
      return isString('title') && isArray('stages') ? (block as CycleBlock) : null
    case 'comparison':
      return isString('title') && isArray('columns') && (value.columns as unknown[]).length === 2
        ? (block as ComparisonBlock)
        : null
    case 'tree':
      return isString('title') && isString('root') && isArray('branches') ? (block as TreeBlock) : null
    default:
      return null
  }
}
