import InsertDriveFileOutlinedIcon from '@mui/icons-material/InsertDriveFileOutlined'
import { Alert, AlertTitle, Box, Button, Paper, Stack, Typography } from '@mui/material'
import { useEffect } from 'react'
import { useNavigate } from 'react-router'
import { brand } from '../app/theme'
import { PageHeader } from '../components/common/PageHeader'
import { Panel } from '../components/common/Panel'
import { FileDropzone } from '../components/video/FileDropzone'
import { UploadProgress } from '../components/video/UploadProgress'
import { useVideoUpload } from '../hooks/useVideoUpload'
import { correlationIdOf, describeError } from '../utils/errorMessages'
import { formatBytes } from '../utils/formatBytes'

export function UploadPage() {
  const navigate = useNavigate()
  const { state, start, retry, cancel, reset } = useVideoUpload()
  const { phase, file, error } = state
  const busy = phase !== 'idle' && phase !== 'error' && phase !== 'done'

  useEffect(() => {
    if (phase === 'done' && state.video) {
      void navigate(`/videos/${state.video.id}`, { replace: true, state: { uploaded: true } })
    }
  }, [phase, state.video, navigate])

  return (
    <>
      <PageHeader
        title="Enviar vídeo"
        description="O arquivo vai direto para o armazenamento, sem passar pelos nossos servidores."
        back={{ to: '/videos', label: 'Meus vídeos' }}
      />
      <Box sx={{ display: 'grid', gap: 3, gridTemplateColumns: { xs: '1fr', md: '7fr 5fr' }, alignItems: 'start' }}>
      <Box sx={{ minWidth: 0 }}>

      {phase === 'idle' && <FileDropzone onFile={(selected) => void start(selected)} />}

      {phase !== 'idle' && file && (
        <Paper variant="outlined" sx={{ p: { xs: 2.5, md: 3 } }}>
          <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', mb: 3 }}>
            <InsertDriveFileOutlinedIcon sx={{ color: 'text.secondary' }} />
            <Box sx={{ minWidth: 0 }}>
              <Typography sx={{ fontWeight: 600, overflowWrap: 'anywhere' }}>{file.name}</Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                {formatBytes(file.size)}
              </Typography>
            </Box>
          </Stack>

          {phase === 'error' ? (
            <Alert
              severity="error"
              variant="outlined"
              action={
                <Stack direction="row" spacing={1}>
                  <Button color="inherit" size="small" onClick={reset}>
                    Outro arquivo
                  </Button>
                  {!state.rejected && (
                    <Button color="inherit" size="small" variant="outlined" onClick={retry}>
                      Tentar novamente
                    </Button>
                  )}
                </Stack>
              }
            >
              <AlertTitle>{state.rejected ? 'Arquivo não aceito' : 'O envio falhou'}</AlertTitle>
              {describeError(error)}
              {correlationIdOf(error) && (
                <Typography variant="caption" component="p" sx={{ mt: 0.5, opacity: 0.8 }}>
                  Código da requisição: {correlationIdOf(error)}
                </Typography>
              )}
            </Alert>
          ) : (
            <Stack spacing={3}>
              <UploadProgress phase={phase} progress={state.progress} />
              <Box>
                <Button color="inherit" onClick={cancel} disabled={!busy}>
                  Cancelar envio
                </Button>
              </Box>
            </Stack>
          )}
        </Paper>
      )}
      </Box>
      <AfterUpload />
      </Box>
    </>
  )
}

/** O que acontece depois do envio, para o usuário saber o que esperar antes de escolher o arquivo. */
function AfterUpload() {
  const steps = [
    { title: 'Envio direto', text: 'O vídeo sobe do seu navegador para o armazenamento. Você acompanha o percentual.' },
    { title: 'Escolha o que gerar', text: 'Transcrição com timestamps, resumo e capítulos com diagramas, juntos ou separados.' },
    { title: 'Processamento em segundo plano', text: 'O trabalho continua no servidor mesmo que você feche a tela; o andamento fica salvo.' },
    { title: 'Estude pelo resultado', text: 'Clique num capítulo ou num trecho da transcrição para ir ao momento exato do vídeo.' },
  ]
  return (
    <Panel title="Depois do envio" titleId="after-upload-title" accent="teal">
      <Stack component="ol" spacing={2} sx={{ listStyle: 'none', p: 0, m: 0 }}>
        {steps.map((step) => (
          <Box component="li" key={step.title} sx={{ pl: 2, borderLeft: `2px solid ${brand.tealTint}` }}>
            <Typography sx={{ fontWeight: 650, color: brand.ink }}>{step.title}</Typography>
            <Typography variant="body2" sx={{ color: brand.muted }}>
              {step.text}
            </Typography>
          </Box>
        ))}
      </Stack>
    </Panel>
  )
}
