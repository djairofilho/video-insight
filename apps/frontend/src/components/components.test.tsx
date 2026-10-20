import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { completedJob, jobResult } from '../mocks/fixtures'
import { ApiError } from '../services/apiClient'
import { renderWithTheme } from '../test/render'
import type { Operation } from '../types/job'
import { ErrorState } from './common/States'
import { JobProgress } from './job/JobStatusPanel'
import { OperationSelector } from './job/OperationSelector'
import { ChapterBlocks } from './result/blocks/ChapterBlocks'
import { ChapterList } from './result/ChapterList'
import { ChapterTimeline } from './result/ChapterTimeline'
import { TranscriptPanel } from './result/TranscriptPanel'
import { UploadProgress } from './video/UploadProgress'

function SelectorHarness({ onChange }: { onChange: (operations: Operation[]) => void }) {
  const [value, setValue] = useState<Operation[]>(['transcription'])
  return (
    <OperationSelector
      value={value}
      onChange={(next) => {
        setValue(next)
        onChange(next)
      }}
    />
  )
}

describe('OperationSelector', () => {
  it('alterna as operações mantendo a ordem do pipeline', async () => {
    const onChange = vi.fn()
    renderWithTheme(<SelectorHarness onChange={onChange} />)

    await userEvent.click(screen.getByRole('checkbox', { name: /Capítulos/ }))
    expect(onChange).toHaveBeenLastCalledWith(['transcription', 'chapters'])
    await userEvent.click(screen.getByRole('checkbox', { name: /Resumo/ }))
    expect(onChange).toHaveBeenLastCalledWith(['transcription', 'summary', 'chapters'])
    await userEvent.click(screen.getByRole('checkbox', { name: /Transcrição/ }))
    expect(onChange).toHaveBeenLastCalledWith(['summary', 'chapters'])
  })
})

describe('barras de progresso', () => {
  it('mostra o percentual do upload', () => {
    renderWithTheme(<UploadProgress phase="uploading" progress={42} />)
    expect(screen.getByRole('progressbar', { name: 'Progresso do envio' })).toHaveAttribute('aria-valuenow', '42')
    expect(screen.getByText('42%')).toBeInTheDocument()
  })

  it('mostra a etapa atual e o percentual estimado do job', () => {
    renderWithTheme(<JobProgress job={{ ...completedJob, status: 'processing', stage: 'transcribing', progress_percent: 55 }} />)
    expect(screen.getByRole('progressbar', { name: 'Progresso estimado do processamento' })).toHaveAttribute('aria-valuenow', '55')
    expect(screen.getAllByText('Transcrevendo')[0]).toBeInTheDocument()
    const steps = screen.getByRole('list', { name: 'Etapas do processamento' })
    expect(steps.querySelector('[aria-current="step"]')).toHaveTextContent('Transcrevendo')
  })

  it('não mostra percentual enquanto o job está na fila', () => {
    renderWithTheme(<JobProgress job={{ ...completedJob, status: 'queued', stage: undefined, progress_percent: 0 }} />)
    expect(screen.getByText('Aguardando na fila')).toBeInTheDocument()
    expect(screen.queryByText('0%')).not.toBeInTheDocument()
  })
})

describe('navegação por timestamp', () => {
  it('leva o player ao início do capítulo clicado', async () => {
    const onSeek = vi.fn()
    renderWithTheme(<ChapterList chapters={jobResult.chapters!} activeIndex={1} onSeek={onSeek} />)

    await userEvent.click(screen.getByRole('button', { name: /02:11: O ciclo do carbono/ }))
    expect(onSeek).toHaveBeenCalledWith(131)
    expect(screen.getByRole('button', { name: /01:12/ })).toHaveAttribute('aria-current', 'true')
  })

  it('leva o player ao segmento clicado e destaca o ativo', async () => {
    const onSeek = vi.fn()
    renderWithTheme(<TranscriptPanel jobId="job" segments={jobResult.transcript} activeIndex={2} onSeek={onSeek} />)

    await userEvent.click(screen.getByText('Começamos pela fotossíntese.'))
    expect(onSeek).toHaveBeenCalledWith(10.8)
    expect(screen.getByText('Começamos pela fotossíntese.').closest('button')).toHaveAttribute('aria-current', 'true')
  })
})

describe('linha do tempo dos capítulos', () => {
  it('divide a duração nos capítulos, marca o atual e leva ao início do clicado', async () => {
    const onSeek = vi.fn()
    renderWithTheme(
      <ChapterTimeline chapters={jobResult.chapters!} duration={195.4} currentTime={80} activeIndex={1} onSeek={onSeek} />,
    )
    const timeline = screen.getByRole('group', { name: 'Linha do tempo dos capítulos' })
    const segments = within(timeline).getAllByRole('button')
    expect(segments).toHaveLength(3)
    expect(segments[1]).toHaveAttribute('aria-current', 'true')
    expect(screen.getByText('2. Respiração celular e comparação de processos')).toBeInTheDocument()
    expect(screen.getByText('01:20 / 03:15')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Capítulo 3: O ciclo do carbono/ }))
    expect(onSeek).toHaveBeenCalledWith(131)
  })
})

describe('blocos dos capítulos', () => {
  it('renderiza os tipos do contrato e não quebra com tipos desconhecidos', () => {
    renderWithTheme(
      <ChapterBlocks
        blocks={[
          { type: 'paragraph', text: 'Texto com **destaque**.' },
          { type: 'callout', variant: 'warning', title: 'Cuidado', text: 'Leia isto.' },
          { type: 'flow', title: 'Etapas', steps: [{ label: 'A' }, { label: 'B', detail: 'depois' }] },
          { type: 'hologram' },
        ]}
      />,
    )
    expect(screen.getByText('destaque').tagName).toBe('STRONG')
    expect(screen.getByText('Atenção')).toBeInTheDocument()
    expect(screen.getByRole('figure', { name: 'Etapas' })).toHaveTextContent('depois')
    expect(screen.getByText('Conteúdo indisponível nesta versão.')).toBeInTheDocument()
  })

  it('descarta HTML do Markdown gerado pela IA', () => {
    renderWithTheme(<ChapterBlocks blocks={[{ type: 'paragraph', text: 'Oi <img src=x onerror="alert(1)"> **mundo**' }]} />)
    expect(document.querySelector('img')).toBeNull()
    expect(screen.getByText('mundo')).toBeInTheDocument()
  })
})

describe('mensagens de erro', () => {
  it('mostra a mensagem, o código da requisição e a ação de nova tentativa', async () => {
    const onRetry = vi.fn()
    const error = new ApiError('x', 503, { code: 'VIDEO_SERVICE_UNAVAILABLE', message: 'x', correlation_id: 'corr-42' })
    renderWithTheme(<ErrorState error={error} onRetry={onRetry} />)

    expect(screen.getByText(/serviço de vídeos está indisponível/)).toBeInTheDocument()
    expect(screen.getByText('Código da requisição: corr-42')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })
})
