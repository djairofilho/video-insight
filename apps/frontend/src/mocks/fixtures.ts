import type { Job } from '../types/job'
import type { JobResult } from '../types/result'
import type { Video } from '../types/video'

/** Dados de exemplo usados pelos testes e pelo modo mock (`VITE_USE_MOCKS=true`). */
export const VIDEO_ID = '7a1d2c3e-0b4f-4e5a-9c8d-1e2f3a4b5c6d'
export const JOB_ID = 'c0ffee00-1234-4abc-8def-001122334455'

export const readyVideo: Video = {
  id: VIDEO_ID,
  file_name: 'aula-fotossintese.mp4',
  content_type: 'video/mp4',
  size_bytes: 48_234_496,
  duration_seconds: 195.4,
  upload_status: 'ready',
  created_at: '2026-10-19T14:30:00Z',
  updated_at: '2026-10-19T14:31:10Z',
}

/** Outros vídeos da biblioteca de exemplo, um em cada estado, para a lista mostrar os casos reais. */
export const libraryVideos: Video[] = [
  {
    id: '2b6f9e10-3c4d-4e5f-8a7b-9c0d1e2f3a4b',
    file_name: 'seminario-mecanica-quantica.mp4',
    content_type: 'video/mp4',
    size_bytes: 87_031_808,
    duration_seconds: 562.8,
    upload_status: 'ready',
    created_at: '2026-10-18T19:05:00Z',
  },
  {
    id: '3c7a0f21-4d5e-4f60-9b8c-0d1e2f3a4b5c',
    file_name: 'entrevista-orientadora.mp4',
    content_type: 'video/mp4',
    size_bytes: 31_457_280,
    upload_status: 'uploading',
    created_at: '2026-10-17T13:20:00Z',
  },
  {
    id: '4d8b1032-5e6f-4071-8c9d-1e2f3a4b5c6d',
    file_name: 'revisao-prova-calculo.mp4',
    content_type: 'video/mp4',
    size_bytes: 64_225_280,
    upload_status: 'failed',
    created_at: '2026-10-15T09:45:00Z',
  },
]

export const completedJob: Job = {
  id: JOB_ID,
  video_id: VIDEO_ID,
  operations: ['transcription', 'summary', 'chapters'],
  status: 'completed',
  stage: 'uploading_artifacts',
  progress_percent: 100,
  attempt: 1,
  created_at: '2026-10-19T14:32:00Z',
  updated_at: '2026-10-19T14:34:40Z',
}

export const jobResult: JobResult = {
  job_id: JOB_ID,
  video_id: VIDEO_ID,
  completed_at: '2026-10-19T14:34:40Z',
  models: [
    { purpose: 'transcription', provider: 'groq', model: 'whisper-large-v3-turbo', version: '1' },
    { purpose: 'summary', provider: 'google', model: 'gemini-3.5-flash-lite', version: '1' },
    { purpose: 'chapters', provider: 'google', model: 'gemini-3.5-flash-lite', version: '1' },
  ],
  transcript: [
    { start_seconds: 0, end_seconds: 2.4, text: 'Olá, turma!' },
    { start_seconds: 2.4, end_seconds: 10.8, text: 'Hoje vamos entender como as plantas produzem o próprio alimento e como os seres vivos usam essa energia.' },
    { start_seconds: 10.8, end_seconds: 14, text: 'Começamos pela fotossíntese.' },
    { start_seconds: 14, end_seconds: 22.6, text: 'A fotossíntese acontece principalmente nas folhas, dentro de estruturas chamadas cloroplastos.' },
    { start_seconds: 22.6, end_seconds: 30, text: 'Nos cloroplastos existe um pigmento verde, a clorofila, que absorve a luz do sol.' },
    { start_seconds: 30, end_seconds: 41.5, text: 'A planta também retira água do solo pelas raízes e gás carbônico do ar pelos estômatos.' },
    { start_seconds: 41.5, end_seconds: 55, text: 'Com a energia da luz, ela transforma água e gás carbônico em glicose e libera oxigênio.' },
    { start_seconds: 55, end_seconds: 72, text: 'Essa glicose é a reserva de energia que a planta usa para crescer.' },
    { start_seconds: 72, end_seconds: 86, text: 'Mas como essa energia é liberada? É aí que entra a respiração celular.' },
    { start_seconds: 86, end_seconds: 101, text: 'A respiração acontece nas mitocôndrias de plantas, animais, fungos e quase todos os seres vivos.' },
    { start_seconds: 101, end_seconds: 118, text: 'Ela consome oxigênio e libera gás carbônico, o contrário da fotossíntese.' },
    { start_seconds: 118, end_seconds: 131, text: 'E atenção: as plantas também respiram, vinte e quatro horas por dia.' },
    { start_seconds: 131, end_seconds: 150, text: 'Juntos, esses dois processos formam o ciclo do carbono.' },
    { start_seconds: 150, end_seconds: 172, text: 'Os animais comem as plantas, usam a glicose na respiração e devolvem o gás carbônico para o ar.' },
    { start_seconds: 172, end_seconds: 195.4, text: 'Para pensar: o que aconteceria se todas as plantas de uma região desaparecessem?' },
  ],
  summary: [
    'As plantas produzem o próprio alimento pela **fotossíntese** e usam essa energia pela **respiração celular**. Juntos, os dois processos formam um ciclo essencial para o equilíbrio entre os seres vivos e o ambiente.',
    '',
    '## Fotossíntese',
    '',
    '- **Onde ocorre:** nos cloroplastos das folhas, com a ajuda da clorofila.',
    '- **Entradas:** água do solo, gás carbônico do ar e energia da luz.',
    '- **Saídas:** glicose e oxigênio.',
    '',
    '## Respiração celular',
    '',
    '- **Onde ocorre:** nas mitocôndrias de quase todos os seres vivos.',
    '- **Funcionamento contínuo:** consome oxigênio e libera gás carbônico o tempo todo, inclusive nas plantas.',
  ].join('\n'),
  chapters: [
    {
      title: 'O processo da fotossíntese',
      start_seconds: 0,
      end_seconds: 72,
      blocks: [
        { type: 'paragraph', text: 'A fotossíntese acontece principalmente nas folhas, dentro de estruturas chamadas **cloroplastos**.' },
        { type: 'paragraph', text: 'Nos cloroplastos existe a **clorofila**, um pigmento verde que absorve a luz do sol. A planta também retira água do solo e gás carbônico do ar por aberturas chamadas **estômatos**.' },
        {
          type: 'flow',
          title: 'Etapas da fotossíntese',
          steps: [
            { label: 'Luz solar', detail: 'Absorvida pela clorofila' },
            { label: 'Água', detail: 'Retirada do solo pelas raízes' },
            { label: 'Gás carbônico', detail: 'Capturado pelos estômatos' },
            { label: 'Glicose', detail: 'Açúcar produzido com a energia da luz' },
          ],
        },
        { type: 'callout', variant: 'definition', title: 'Clorofila', text: 'Pigmento verde dos cloroplastos que **absorve a luz** usada na fotossíntese.' },
      ],
    },
    {
      title: 'Respiração celular e comparação de processos',
      start_seconds: 72,
      end_seconds: 131,
      blocks: [
        { type: 'paragraph', text: 'A glicose guarda energia, mas a planta precisa liberá-la para crescer. É aí que entra a **respiração celular**, que acontece nas **mitocôndrias**.' },
        {
          type: 'comparison',
          title: 'Fotossíntese × respiração',
          columns: [
            { heading: 'Fotossíntese', items: ['Consome gás carbônico', 'Libera oxigênio', 'Só com luz'] },
            { heading: 'Respiração', items: ['Consome oxigênio', 'Libera gás carbônico', 'O tempo todo'] },
          ],
          shared: 'Os dois processos envolvem a glicose',
        },
        { type: 'callout', variant: 'warning', title: 'As plantas respiram', text: 'Muitas pessoas acham que as plantas só fazem fotossíntese, mas elas respiram vinte e quatro horas por dia.' },
      ],
    },
    {
      title: 'O ciclo do carbono e reflexão final',
      start_seconds: 131,
      end_seconds: 195.4,
      blocks: [
        { type: 'paragraph', text: 'Juntas, a fotossíntese e a respiração formam o **ciclo do carbono**, que mantém o equilíbrio entre os seres vivos e o ambiente.' },
        {
          type: 'cycle',
          title: 'Ciclo do carbono',
          stages: ['Planta capta gás', 'Planta produz glicose', 'Animal consome planta', 'Respiração devolve gás'],
          center: 'Carbono circulando',
        },
        {
          type: 'tree',
          title: 'Quem participa do ciclo',
          root: 'Ciclo do carbono',
          branches: [
            { label: 'Produtores', children: ['Plantas', 'Algas'] },
            { label: 'Consumidores', children: ['Herbívoros', 'Carnívoros'] },
            { label: 'Decompositores', children: ['Fungos', 'Bactérias'] },
          ],
        },
        { type: 'callout', variant: 'reflection', title: 'O impacto da ausência de plantas', text: 'Se todas as plantas de uma região desaparecessem, o que aconteceria com o gás carbônico do ar e com os animais que vivem ali?' },
      ],
    },
  ],
}
