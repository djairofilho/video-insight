import { brand } from '../../../app/theme'

/** Tons dos diagramas tirados da marca: azul, turquesa e dois neutros quentes para separar etapas vizinhas. */
const HUES = [
  { border: brand.blue, fill: brand.blueTint },
  { border: brand.teal, fill: brand.tealTint },
  { border: '#d4952b', fill: '#fdf3e1' },
  { border: '#5f6a85', fill: '#eef1f6' },
] as const

export function diagramColor(index: number) {
  return HUES[index % HUES.length]
}
