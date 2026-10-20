import { describe, expect, it } from 'vitest'
import { completedJob } from '../mocks/fixtures'
import { ApiError } from '../services/apiClient'
import { UploadError } from '../services/videoService'
import { asKnownBlock } from './blocks'
import { correlationIdOf, describeError } from './errorMessages'
import { findActiveIndex } from './findActiveIndex'
import { formatBytes } from './formatBytes'
import { formatDuration } from './formatDuration'
import { formatTimestamp } from './formatTimestamp'
import { createIdempotencyKeyStore } from './idempotency'
import { jobLink, stagesFor } from './jobs'
import { MAX_VIDEO_BYTES, validateVideoDuration, validateVideoFile } from './validateVideoFile'

const mp4 = (size: number, type = 'video/mp4') => new File([new Uint8Array(Math.min(size, 16))], 'aula.mp4', { type })

function sized(file: File, size: number): File {
  Object.defineProperty(file, 'size', { value: size })
  return file
}

describe('formatBytes', () => {
  it('converte para a maior unidade binária', () => {
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(1536)).toBe('1,5 KB')
    expect(formatBytes(MAX_VIDEO_BYTES)).toBe('100 MB')
    expect(formatBytes(48_234_496)).toBe('46 MB')
  })

  it('não formata valores inválidos', () => {
    expect(formatBytes(-1)).toBe('—')
    expect(formatBytes(Number.NaN)).toBe('—')
  })
})

describe('formatTimestamp', () => {
  it('usa mm:ss abaixo de uma hora e hh:mm:ss acima', () => {
    expect(formatTimestamp(0)).toBe('00:00')
    expect(formatTimestamp(72.9)).toBe('01:12')
    expect(formatTimestamp(599)).toBe('09:59')
    expect(formatTimestamp(3725)).toBe('01:02:05')
  })

  it('trata valores negativos ou inválidos como zero', () => {
    expect(formatTimestamp(-5)).toBe('00:00')
    expect(formatTimestamp(Number.POSITIVE_INFINITY)).toBe('00:00')
  })
})

describe('formatDuration', () => {
  it('escreve minutos e segundos', () => {
    expect(formatDuration(195.4)).toBe('3 min 15 s')
    expect(formatDuration(120)).toBe('2 min')
    expect(formatDuration(42)).toBe('42 s')
    expect(formatDuration(undefined)).toBe('—')
  })
})

describe('validação do arquivo', () => {
  it('aceita MP4 dentro do limite', () => {
    expect(validateVideoFile(sized(mp4(10), 1024))).toBeNull()
  })

  it('rejeita outros formatos, arquivo vazio e arquivo grande demais', () => {
    expect(validateVideoFile(mp4(10, 'video/quicktime'))).toBe('Envie um arquivo no formato MP4.')
    expect(validateVideoFile(sized(mp4(0), 0))).toBe('O arquivo está vazio.')
    expect(validateVideoFile(sized(mp4(10), MAX_VIDEO_BYTES + 1))).toBe('O arquivo passa do limite de 100 MB.')
    expect(validateVideoFile(sized(mp4(10), MAX_VIDEO_BYTES))).toBeNull()
  })

  it('limita a duração a 10 minutos', () => {
    expect(validateVideoDuration(600)).toBeNull()
    expect(validateVideoDuration(600.5)).toBe('O vídeo passa do limite de 10 minutos.')
    expect(validateVideoDuration(Number.NaN)).toMatch(/duração/)
  })
})

describe('Idempotency-Key', () => {
  it('reaproveita a chave até ser reiniciada', () => {
    let counter = 0
    const store = createIdempotencyKeyStore(() => `chave-${++counter}`)
    expect(store.current()).toBe('chave-1')
    expect(store.current()).toBe('chave-1')
    store.reset()
    expect(store.current()).toBe('chave-2')
  })

  it('gera UUIDs aceitos pelo contrato (16 a 128 caracteres)', () => {
    const key = createIdempotencyKeyStore().current()
    expect(key.length).toBeGreaterThanOrEqual(16)
    expect(key.length).toBeLessThanOrEqual(128)
  })
})

describe('findActiveIndex', () => {
  const segments = [
    { start_seconds: 0, end_seconds: 2 },
    { start_seconds: 2, end_seconds: 5 },
    { start_seconds: 6, end_seconds: 9 },
  ]

  it('encontra o intervalo que contém o instante', () => {
    expect(findActiveIndex(segments, 0)).toBe(0)
    expect(findActiveIndex(segments, 2)).toBe(1)
    expect(findActiveIndex(segments, 8.9)).toBe(2)
  })

  it('devolve -1 nas pausas e fora do vídeo', () => {
    expect(findActiveIndex(segments, 5.5)).toBe(-1)
    expect(findActiveIndex(segments, 12)).toBe(-1)
    expect(findActiveIndex([], 1)).toBe(-1)
  })
})

describe('blocos dos capítulos', () => {
  it('aceita os tipos do contrato com os campos obrigatórios', () => {
    expect(asKnownBlock({ type: 'paragraph', text: 'Olá' } as never)).not.toBeNull()
    expect(asKnownBlock({ type: 'callout', variant: 'warning', title: 'T', text: 'x' } as never)).not.toBeNull()
  })

  it('trata tipos desconhecidos ou incompletos como indisponíveis', () => {
    expect(asKnownBlock({ type: 'video-clip' })).toBeNull()
    expect(asKnownBlock({ type: 'flow', title: 'Sem passos' })).toBeNull()
    expect(asKnownBlock({ type: 'callout', variant: 'sarcasm', title: 'T', text: 'x' } as never)).toBeNull()
  })
})

describe('jobs', () => {
  it('lista só as etapas das operações pedidas', () => {
    expect(stagesFor({ ...completedJob, operations: ['transcription'] })).toEqual([
      'downloading',
      'extracting_audio',
      'transcribing',
      'uploading_artifacts',
    ])
    expect(stagesFor(completedJob)).toContain('creating_chapters')
  })

  it('abre o resultado só quando o job terminou', () => {
    expect(jobLink(completedJob)).toBe(`/jobs/${completedJob.id}/result`)
    expect(jobLink({ ...completedJob, status: 'processing' })).toBe(`/jobs/${completedJob.id}`)
  })
})

describe('mensagens de erro', () => {
  it('traduz códigos conhecidos e preserva o correlation_id', () => {
    const error = new ApiError('x', 409, { code: 'VIDEO_NOT_READY', message: 'msg', correlation_id: 'abc' })
    expect(describeError(error)).toBe('O envio do vídeo ainda não foi confirmado.')
    expect(correlationIdOf(error)).toBe('abc')
  })

  it('usa a mensagem da API para códigos desconhecidos', () => {
    expect(describeError(new ApiError('x', 400, { code: 'NOVO', message: 'Mensagem da API', correlation_id: 'c' }))).toBe(
      'Mensagem da API',
    )
  })

  it('explica sessão expirada, falha de rede e erros de upload', () => {
    expect(describeError(new ApiError('x', 401))).toMatch(/sessão expirou/)
    expect(describeError(new ApiError('x', 0))).toMatch(/conectar ao servidor/)
    expect(describeError(new UploadError('A autorização de envio expirou.', 403))).toBe('A autorização de envio expirou.')
    expect(describeError('???')).toBe('Algo deu errado. Tente novamente.')
  })
})
