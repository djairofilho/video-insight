import { useEffect, useEffectEvent, useState } from 'react'

export type ResourceState<T> =
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: unknown }

type Settled<T> = Exclude<ResourceState<T>, { status: 'loading' }> & { key: string; attempt: number }

/**
 * Carrega um recurso sempre que `key` muda, cancelando a requisição anterior. O estado guarda a chave que o produziu,
 * então uma troca de rota mostra "carregando" em vez do dado antigo.
 */
export function useAsyncResource<T>(key: string, load: (signal: AbortSignal) => Promise<T>) {
  const [attempt, setAttempt] = useState(0)
  const [settled, setSettled] = useState<Settled<T> | null>(null)
  const runLoad = useEffectEvent(load)

  useEffect(() => {
    const controller = new AbortController()
    runLoad(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) {
          setSettled({ key, attempt, status: 'success', data })
        }
      },
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setSettled({ key, attempt, status: 'error', error })
        }
      },
    )
    return () => controller.abort()
  }, [key, attempt])

  const state: ResourceState<T> =
    settled && settled.key === key && settled.attempt === attempt ? settled : { status: 'loading' }

  return {
    state,
    reload: () => setAttempt((value) => value + 1),
    /** Substitui o dado carregado, por exemplo com a resposta de uma mutação. */
    setData: (data: T) => setSettled({ key, attempt, status: 'success', data }),
  }
}
