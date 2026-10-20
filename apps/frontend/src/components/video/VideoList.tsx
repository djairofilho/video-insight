import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded'
import {
  Box,
  IconButton,
  Link,
  Paper,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import type { MouseEvent } from 'react'
import { Link as RouterLink, useNavigate } from 'react-router'
import { brand } from '../../app/theme'
import type { Video } from '../../types/video'
import { formatBytes } from '../../utils/formatBytes'
import { formatDateTime, formatDuration } from '../../utils/formatDuration'
import { UploadStatusChip } from '../common/StatusChip'
import { VideoThumbnail } from './VideoThumbnail'

interface VideoListProps {
  videos: Video[]
  onDelete: (video: Video) => void
}

export function VideoList({ videos, onDelete }: VideoListProps) {
  const theme = useTheme()
  const compact = useMediaQuery(theme.breakpoints.down('md'))
  return compact ? <VideoCards videos={videos} onDelete={onDelete} /> : <VideoTable videos={videos} onDelete={onDelete} />
}

function VideoName({ video }: { video: Video }) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Link
        component={RouterLink}
        to={`/videos/${video.id}`}
        sx={{ color: brand.ink, fontWeight: 650, overflowWrap: 'anywhere' }}
      >
        {video.file_name}
      </Link>
      <Typography variant="body2" sx={{ color: brand.faint, mt: 0.25 }}>
        MP4 · {formatBytes(video.size_bytes)}
      </Typography>
    </Box>
  )
}

function DeleteButton({ video, onDelete }: { video: Video; onDelete: (video: Video) => void }) {
  return (
    <Tooltip title="Excluir vídeo">
      <IconButton
        aria-label={`Excluir ${video.file_name}`}
        onClick={() => onDelete(video)}
        size="small"
        sx={{ color: brand.faint, '&:hover': { color: brand.negative } }}
      >
        <DeleteOutlineRoundedIcon fontSize="small" />
      </IconButton>
    </Tooltip>
  )
}

const ROW_HOVER = { cursor: 'pointer', '&:hover': { bgcolor: '#f8fafd' } }

/** A linha inteira abre o vídeo; o teclado usa o link do nome, e cliques em botões ou links seguem o próprio alvo. */
function useOpenOnRowClick() {
  const navigate = useNavigate()
  return (video: Video) => (event: MouseEvent<HTMLElement>) => {
    if ((event.target as HTMLElement).closest('a, button')) return
    void navigate(`/videos/${video.id}`)
  }
}

function VideoTable({ videos, onDelete }: VideoListProps) {
  const openRow = useOpenOnRowClick()
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table aria-label="Vídeos enviados">
        <TableHead>
          <TableRow>
            <TableCell sx={{ pl: 3 }}>Vídeo</TableCell>
            <TableCell align="right">Duração</TableCell>
            <TableCell>Enviado em</TableCell>
            <TableCell>Estado</TableCell>
            <TableCell align="right" sx={{ pr: 2 }}>
              <Box component="span" sx={visuallyHidden}>Ações</Box>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {videos.map((video) => (
            <TableRow key={video.id} onClick={openRow(video)} sx={{ ...ROW_HOVER, '&:last-child td': { borderBottom: 0 } }}>
              <TableCell sx={{ pl: 3, maxWidth: 520 }}>
                <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
                  <VideoThumbnail video={video} />
                  <VideoName video={video} />
                </Stack>
              </TableCell>
              <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                {formatDuration(video.duration_seconds)}
              </TableCell>
              <TableCell sx={{ whiteSpace: 'nowrap', color: brand.muted }}>{formatDateTime(video.created_at)}</TableCell>
              <TableCell>
                <UploadStatusChip status={video.upload_status} />
              </TableCell>
              <TableCell align="right" sx={{ pr: 2 }}>
                <DeleteButton video={video} onDelete={onDelete} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function VideoCards({ videos, onDelete }: VideoListProps) {
  const openRow = useOpenOnRowClick()
  return (
    <Stack component="ul" spacing={1.5} sx={{ listStyle: 'none', p: 0, m: 0 }} aria-label="Vídeos enviados">
      {videos.map((video) => (
        <Paper component="li" key={video.id} variant="outlined" onClick={openRow(video)} sx={{ p: 1.5, cursor: 'pointer' }}>
          <Stack direction="row" spacing={1.5} sx={{ alignItems: 'flex-start' }}>
            <VideoThumbnail video={video} width={96} />
            <Box sx={{ minWidth: 0, flexGrow: 1 }}>
              <VideoName video={video} />
              <Stack direction="row" spacing={1} sx={{ mt: 1, alignItems: 'center', flexWrap: 'wrap' }} useFlexGap>
                <UploadStatusChip status={video.upload_status} />
                <Typography variant="body2" sx={{ color: brand.faint }}>
                  {formatDuration(video.duration_seconds)}
                </Typography>
              </Stack>
            </Box>
            <DeleteButton video={video} onDelete={onDelete} />
          </Stack>
        </Paper>
      ))}
    </Stack>
  )
}

/** Mesmo layout da tabela com cada valor trocado por um bloco cinza do tamanho real: nada pula quando os dados chegam. */
export function VideoListSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <TableContainer component={Paper} variant="outlined" role="status" aria-label="Carregando seus vídeos">
      <Table>
        <TableHead>
          <TableRow>
            <TableCell sx={{ pl: 3 }}>Vídeo</TableCell>
            <TableCell align="right">Duração</TableCell>
            <TableCell>Enviado em</TableCell>
            <TableCell>Estado</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {Array.from({ length: rows }, (_, index) => (
            <TableRow key={index} sx={{ '&:last-child td': { borderBottom: 0 } }}>
              <TableCell sx={{ pl: 3 }}>
                <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
                  <Skeleton variant="rounded" width={112} height={63} animation="pulse" />
                  <Box>
                    <Skeleton width={200} height={22} animation="pulse" />
                    <Skeleton width={90} height={18} animation="pulse" />
                  </Box>
                </Stack>
              </TableCell>
              <TableCell align="right"><Skeleton width={60} sx={{ ml: 'auto' }} animation="pulse" /></TableCell>
              <TableCell><Skeleton width={110} animation="pulse" /></TableCell>
              <TableCell><Skeleton variant="rounded" width={64} height={24} sx={{ borderRadius: 999 }} animation="pulse" /></TableCell>
              <TableCell />
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

const visuallyHidden = {
  border: 0,
  clip: 'rect(0 0 0 0)',
  height: '1px',
  margin: '-1px',
  overflow: 'hidden',
  padding: 0,
  position: 'absolute',
  whiteSpace: 'nowrap',
  width: '1px',
} as const
