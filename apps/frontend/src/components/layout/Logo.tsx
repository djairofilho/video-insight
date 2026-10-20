import { Box, Stack } from '@mui/material'
import { brand } from '../../app/theme'

/** Símbolo da marca: o bloco de texto turquesa à frente do play azul, como na logo do projeto. */
export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <Box component="svg" viewBox="0 0 44 34" width={size * (44 / 34)} height={size} aria-hidden sx={{ display: 'block', flexShrink: 0 }}>
      <path d="M17 3.2c0-2.2 2.4-3.6 4.3-2.5l19.4 11.6a4.3 4.3 0 0 1 0 7.4L21.3 31.3c-1.9 1.1-4.3-.3-4.3-2.5Z" fill={brand.blue} />
      <path
        d="M3.4 4.4c0-2.4 2.4-4 4.6-3.2l9.6 3.6a4.6 4.6 0 0 1 3 4.3v18.3a4.6 4.6 0 0 1-6.2 4.3L6.4 29a4.6 4.6 0 0 1-3-4.3Z"
        fill={brand.teal}
        stroke={brand.surface}
        strokeWidth="1.6"
      />
      <g stroke={brand.surface} strokeWidth="2.6" strokeLinecap="round">
        <path d="M7.6 10.6l8.6 3" />
        <path d="M7.6 16.2l8.6 3" />
        <path d="M7.6 21.8l8.6 3" />
      </g>
    </Box>
  )
}

export function Logo() {
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
      <LogoMark />
      <Box
        component="span"
        translate="no"
        sx={{ fontWeight: 750, fontSize: '1.2rem', letterSpacing: '-0.03em', color: brand.ink, lineHeight: 1 }}
      >
        video insight
      </Box>
    </Stack>
  )
}
