import SearchOffRoundedIcon from '@mui/icons-material/SearchOffRounded'
import { Button } from '@mui/material'
import { Link as RouterLink } from 'react-router'
import { EmptyState } from '../components/common/States'

export function NotFoundPage() {
  return (
    <EmptyState
      icon={<SearchOffRoundedIcon />}
      title="Página não encontrada"
      description="O endereço pode estar errado ou o conteúdo foi removido."
      action={
        <Button component={RouterLink} to="/videos" variant="contained">
          Ir para meus vídeos
        </Button>
      }
    />
  )
}
