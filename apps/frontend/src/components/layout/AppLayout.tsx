import AddRoundedIcon from '@mui/icons-material/AddRounded'
import { Box, Button, Link, Stack } from '@mui/material'
import { NavLink, Outlet, Link as RouterLink, useLocation } from 'react-router'
import { brand } from '../../app/theme'
import { Logo } from './Logo'

/** Largura do conteúdo: a mesma em todas as telas, com margens iguais dos dois lados. */
export const CONTENT_MAX_WIDTH = 1280

export function AppLayout() {
  const { pathname } = useLocation()
  const onUploadPage = pathname === '/videos/new'

  return (
    <Box sx={{ minHeight: '100svh', display: 'flex', flexDirection: 'column' }}>
      <Link
        href="#conteudo"
        sx={{
          position: 'absolute',
          left: 16,
          top: -48,
          zIndex: 2000,
          px: 2,
          py: 1,
          bgcolor: 'background.paper',
          borderRadius: '10px',
          '&:focus': { top: 12 },
        }}
      >
        Pular para o conteúdo
      </Link>
      <Box
        component="header"
        sx={{ position: 'sticky', top: 0, zIndex: 1100, bgcolor: brand.surface, borderBottom: 1, borderColor: 'divider' }}
      >
        <Stack
          direction="row"
          spacing={{ xs: 1.5, sm: 4 }}
          sx={{ maxWidth: CONTENT_MAX_WIDTH, mx: 'auto', px: { xs: 2, sm: 3 }, height: { xs: 60, sm: 68 }, alignItems: 'center' }}
        >
          <Box component={RouterLink} to="/videos" aria-label="Video Insight, ir para meus vídeos" sx={{ textDecoration: 'none', display: 'flex' }}>
            <Logo />
          </Box>
          <Box component="nav" aria-label="Principal" sx={{ display: { xs: 'none', sm: 'flex' }, gap: 3, height: '100%' }}>
            <NavItem to="/videos" label="Meus vídeos" />
          </Box>
          <Box sx={{ flexGrow: 1 }} />
          {!onUploadPage && (
            <Button component={RouterLink} to="/videos/new" variant="contained" startIcon={<AddRoundedIcon />}>
              Enviar vídeo
            </Button>
          )}
        </Stack>
      </Box>
      <Box
        component="main"
        id="conteudo"
        tabIndex={-1}
        sx={{ flexGrow: 1, width: '100%', maxWidth: CONTENT_MAX_WIDTH, mx: 'auto', px: { xs: 2, sm: 3 }, py: { xs: 3, md: 4 }, outline: 'none' }}
      >
        <Outlet />
      </Box>
    </Box>
  )
}

/** Item ativo marcado por cor de texto e um traço de 2px na base da barra, sem pílula colorida. */
function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <Box
      component={NavLink}
      to={to}
      end={false}
      sx={{
        display: 'flex',
        alignItems: 'center',
        height: '100%',
        fontWeight: 600,
        fontSize: '0.95rem',
        color: brand.muted,
        textDecoration: 'none',
        borderBottom: '2px solid transparent',
        '&:hover': { color: brand.ink },
        '&.active': { color: brand.ink, borderBottomColor: brand.ink },
        '&:focus-visible': { outline: `2px solid ${brand.blue}`, outlineOffset: 4, borderRadius: '6px' },
      }}
    >
      {label}
    </Box>
  )
}
