import { useEffect, useState } from 'react'
import { LoadingState } from '../components/common/States'
import { AuthErrorPage } from './AuthErrorPage'

/** Um provedor indisponível nunca mantém a aplicação presa no carregamento. */
export function SessionLoading() {
  const [timedOut, setTimedOut] = useState(false)
  useEffect(() => {
    const timer = window.setTimeout(() => setTimedOut(true), 15_000)
    return () => window.clearTimeout(timer)
  }, [])
  return timedOut
    ? <AuthErrorPage message="Não foi possível restaurar sua sessão a tempo. Entre novamente para continuar." />
    : <LoadingState />
}
