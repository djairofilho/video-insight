import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded'
import { List, ListItemButton, ListItemText, Stack, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router'
import { brand } from '../../app/theme'
import type { Job } from '../../types/job'
import { formatDateTime } from '../../utils/formatDuration'
import { jobLink } from '../../utils/jobs'
import { OPERATION_LABELS } from '../../utils/labels'
import { JobStatusChip } from '../common/StatusChip'

export function JobHistory({ jobs }: { jobs: Job[] }) {
  return (
    <List disablePadding aria-label="Processamentos deste vídeo" sx={{ mx: -1 }}>
      {jobs.map((job, index) => (
        <ListItemButton
          key={job.id}
          component={RouterLink}
          to={jobLink(job)}
          sx={{ borderRadius: '10px', px: 1, py: 1, borderTop: index > 0 ? `1px solid ${brand.rule}` : 0 }}
        >
          <ListItemText
            primary={job.operations.map((operation) => OPERATION_LABELS[operation]).join(' · ')}
            secondary={`${formatDateTime(job.created_at)}${job.attempt > 1 ? ` · tentativa ${job.attempt}` : ''}`}
            slotProps={{ primary: { sx: { fontWeight: 600, color: brand.ink } }, secondary: { sx: { color: brand.faint } } }}
          />
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', ml: 2 }}>
            <JobStatusChip status={job.status} />
            <ChevronRightRoundedIcon sx={{ color: brand.faint }} />
          </Stack>
        </ListItemButton>
      ))}
    </List>
  )
}

export function NoJobsYet() {
  return (
    <Typography variant="body2" sx={{ color: brand.muted }}>
      Nenhum processamento ainda. Escolha o que gerar e clique em “Processar vídeo”.
    </Typography>
  )
}
