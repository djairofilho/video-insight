/**
 * Guarda a `Idempotency-Key` de uma submissão. A mesma chave é reaproveitada enquanto a requisição puder ser repetida
 * (por exemplo, depois de um erro de rede), para não criar jobs duplicados. Uma nova submissão, ou uma mudança no
 * pedido, começa com `reset()`.
 */
export interface IdempotencyKeyStore {
  current(): string
  reset(): void
}

export function createIdempotencyKeyStore(generate: () => string = () => crypto.randomUUID()): IdempotencyKeyStore {
  let key: string | null = null
  return {
    current() {
      key ??= generate()
      return key
    },
    reset() {
      key = null
    },
  }
}
