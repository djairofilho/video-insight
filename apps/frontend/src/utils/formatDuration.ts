/** Duração legível, como `3 min 15 s`. Usada em listas; timestamps clicáveis usam `formatTimestamp`. */
export function formatDuration(totalSeconds?: number): string {
  if (totalSeconds === undefined || !Number.isFinite(totalSeconds) || totalSeconds < 0) {
    return '—'
  }
  const rounded = Math.round(totalSeconds)
  const minutes = Math.floor(rounded / 60)
  const seconds = rounded % 60
  if (minutes === 0) {
    return `${seconds} s`
  }
  return seconds === 0 ? `${minutes} min` : `${minutes} min ${seconds} s`
}

const DATE_FORMAT = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

export function formatDateTime(isoDate: string): string {
  const date = new Date(isoDate)
  return Number.isNaN(date.getTime()) ? '—' : DATE_FORMAT.format(date)
}
