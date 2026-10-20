const UNITS = ['B', 'KB', 'MB', 'GB'] as const

/** Formata bytes em unidades binárias (1 MB = 1024 KB), como o limite de 100 MB do MVP. */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return '—'
  }
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024
    unit += 1
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1
  return `${value.toLocaleString('pt-BR', { maximumFractionDigits: digits })} ${UNITS[unit]}`
}
