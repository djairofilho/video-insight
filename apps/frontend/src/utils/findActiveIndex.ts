interface TimeRange {
  start_seconds: number
  end_seconds: number
}

/**
 * Índice do intervalo que contém `seconds`, por busca binária (os segmentos chegam ordenados pelo início). Devolve -1
 * fora de qualquer intervalo, por exemplo numa pausa entre falas.
 */
export function findActiveIndex(ranges: readonly TimeRange[], seconds: number): number {
  let low = 0
  let high = ranges.length - 1
  let candidate = -1
  while (low <= high) {
    const middle = (low + high) >> 1
    if (ranges[middle].start_seconds <= seconds) {
      candidate = middle
      low = middle + 1
    } else {
      high = middle - 1
    }
  }
  return candidate >= 0 && seconds < ranges[candidate].end_seconds ? candidate : -1
}
