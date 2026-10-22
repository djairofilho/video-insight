import { useAuth0 } from '@auth0/auth0-react'
import { Avatar, Box, ButtonBase, Divider, Popover, Stack, Typography } from '@mui/material'
import { useId, useState } from 'react'

/** Exibe somente as informações de perfil que o Auth0 entregou à sessão. */
export function UserProfile() {
  const { user } = useAuth0()
  const [anchor, setAnchor] = useState<HTMLElement | null>(null)
  const id = useId()
  if (!user) return null

  const givenName = [user.given_name, user.family_name].filter(Boolean).join(' ')
  const profileName = user.name && user.name !== user.email && user.name !== user.nickname && !user.name.includes('@') ? user.name : ''
  const fullName = givenName || profileName
  const username = [user['https://video-insight-api/username'], user.preferred_username, user.username]
    .find((value): value is string => typeof value === 'string' && value.trim().length > 0)
  const name = username || fullName || user.nickname || user.email || 'Usuário'
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map((word) => word[0]).join('').toUpperCase()
  const open = Boolean(anchor)

  return (
    <>
      <ButtonBase onClick={(event) => setAnchor(event.currentTarget)}
        aria-label={`Informações da conta de ${name}`} aria-expanded={open}
        aria-haspopup="dialog" aria-controls={open ? id : undefined}
        sx={{ borderRadius: 2, p: 0.5, minWidth: 0, textAlign: 'left', '&.Mui-focusVisible': { outline: '2px solid', outlineColor: 'primary.main', outlineOffset: 2 } }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center', minWidth: 0 }}>
          <Avatar src={user.picture} alt={name} sx={{ width: 34, height: 34, bgcolor: 'primary.main', fontSize: 14 }}>
            {initials}
          </Avatar>
          <Box sx={{ display: { xs: 'none', md: 'block' }, maxWidth: 180, minWidth: 0 }}>
            <Typography variant="body2" noWrap sx={{ fontWeight: 600 }}>{name}</Typography>
            {user.email && user.email !== name && <Typography variant="caption" color="text.secondary" noWrap component="div">{user.email}</Typography>}
          </Box>
        </Stack>
      </ButtonBase>
      <Popover open={open} anchorEl={anchor} onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}>
        <Stack id={id} role="dialog" aria-label="Informações da conta" spacing={1.5}
          sx={{ p: 2.5, width: 300, maxWidth: 'calc(100vw - 32px)', overflowWrap: 'anywhere' }}>
          <Typography variant="subtitle2">Sua conta</Typography>
          <Divider />
          <Box>
            <Typography variant="caption" color="text.secondary">Nome</Typography>
            <Typography variant="body2">{fullName || 'Não informado no cadastro'}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">Nome de usuário</Typography>
            <Typography variant="body2">{username || 'Não informado pelo Auth0'}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">E-mail</Typography>
            <Typography variant="body2">{user.email || 'Não informado'}</Typography>
          </Box>
        </Stack>
      </Popover>
    </>
  )
}
