/** O proxy preserva caminho, query e Host na origem para manter a assinatura S3 válida. */
export function withStorageProxy<T extends { url: string }>(signed: T): T {
  const proxy = import.meta.env.VITE_STORAGE_PROXY_PATH
  if (!proxy) return signed
  const url = new URL(signed.url)
  if (url.protocol !== 'http:') return signed
  return { ...signed, url: `${proxy.replace(/\/$/, '')}${url.pathname}${url.search}` }
}
