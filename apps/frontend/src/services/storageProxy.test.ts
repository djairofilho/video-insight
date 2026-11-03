import { afterEach, expect, it, vi } from 'vitest'
import { withStorageProxy } from './storageProxy'

afterEach(() => vi.unstubAllEnvs())

it('preserva os parâmetros assinados e os headers no proxy de upload', () => {
  vi.stubEnv('VITE_STORAGE_PROXY_PATH', '/storage/')
  const signed = {
    url: 'http://storage.example:8081/videos/id/original.mp4?X-Amz-Credential=a%2Fb&X-Amz-Signature=abc',
    method: 'PUT', headers: { 'Content-Type': 'video/mp4' },
  }
  expect(withStorageProxy(signed)).toEqual({
    ...signed,
    url: '/storage/videos/id/original.mp4?X-Amz-Credential=a%2Fb&X-Amz-Signature=abc',
  })
  expect(signed.url).toMatch(/^http:/)
})

it('encaminha também exportações do bucket de artefatos', () => {
  vi.stubEnv('VITE_STORAGE_PROXY_PATH', '/storage')
  expect(withStorageProxy({ url: 'http://storage/artifacts/jobs/id/transcript.txt?X-Amz-Signature=abc' }).url)
    .toBe('/storage/artifacts/jobs/id/transcript.txt?X-Amz-Signature=abc')
})

it('mantém URLs HTTPS e ambientes sem proxy', () => {
  const secure = { url: 'https://storage.example/videos/id?signature=abc' }
  vi.stubEnv('VITE_STORAGE_PROXY_PATH', '/storage')
  expect(withStorageProxy(secure)).toBe(secure)
  vi.stubEnv('VITE_STORAGE_PROXY_PATH', '')
  const local = { url: 'http://localhost:9000/videos/id' }
  expect(withStorageProxy(local)).toBe(local)
})
