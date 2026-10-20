import { createTheme } from '@mui/material/styles'

/**
 * Identidade do Video Insight, tirada da logo: marinho para texto e ação principal, azul para os dados (capítulo
 * ativo, progresso, trecho em reprodução) e turquesa só para "pronto". Fundo frio, cartões brancos com borda leve,
 * raio suave nos cartões e pílula nos controles.
 */
export const brand = {
  ink: '#0f1b3d',
  muted: '#4a5571',
  faint: '#5f6a85',
  ground: '#f5f7fb',
  surface: '#ffffff',
  raised: '#f0f3f9',
  border: '#e3e8f0',
  rule: '#edf0f6',
  control: '#c9d1df',
  blue: '#0a66ff',
  blueInk: '#0052cc',
  blueTint: '#eaf2ff',
  blueTintStrong: '#d3e4ff',
  teal: '#14a898',
  tealInk: '#0b6f64',
  tealTint: '#e2f5f2',
  negative: '#c4242a',
  negativeTint: '#ffedea',
  negativeInk: '#831c1e',
  warningTint: '#fff6e0',
  warningInk: '#8a4b00',
} as const

const sans = '"Figtree Variable", "Segoe UI", system-ui, sans-serif'

export const theme = createTheme({
  cssVariables: true,
  palette: {
    mode: 'light',
    primary: { main: brand.ink, contrastText: '#ffffff' },
    secondary: { main: brand.blue, contrastText: '#ffffff' },
    info: { main: brand.blue },
    success: { main: brand.tealInk },
    warning: { main: brand.warningInk },
    error: { main: brand.negative },
    background: { default: brand.ground, paper: brand.surface },
    text: { primary: brand.ink, secondary: brand.muted },
    divider: brand.border,
    action: { hover: 'rgba(15, 27, 61, 0.04)', selected: brand.blueTint },
  },
  shape: { borderRadius: 16 },
  typography: {
    fontFamily: sans,
    // Escala de app: 12 / 14 / 16 / 20 / 28. O título nunca vira manchete de landing page.
    h1: {
      fontSize: '1.5rem',
      fontWeight: 700,
      letterSpacing: '-0.02em',
      lineHeight: 1.2,
      textWrap: 'balance',
      '@media (min-width: 900px)': { fontSize: '1.75rem' },
    },
    h2: { fontSize: '1.25rem', fontWeight: 650, letterSpacing: '-0.01em', lineHeight: 1.3, textWrap: 'balance' },
    h3: { fontSize: '1rem', fontWeight: 650, lineHeight: 1.4 },
    h4: { fontSize: '1rem', fontWeight: 600, lineHeight: 1.4 },
    body1: { fontSize: '1rem', lineHeight: 1.6 },
    body2: { fontSize: '0.875rem', lineHeight: 1.5 },
    caption: { fontSize: '0.75rem', lineHeight: 1.45 },
    overline: { fontSize: '0.875rem', fontWeight: 600, letterSpacing: 0, textTransform: 'none', lineHeight: 1.5 },
    button: { textTransform: 'none', fontWeight: 600, letterSpacing: 0 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { fontVariantNumeric: 'tabular-nums' },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { borderRadius: 999, paddingInline: 18, minHeight: 36 },
        sizeLarge: { minHeight: 44, paddingInline: 22, fontSize: '1rem' },
        sizeSmall: { minHeight: 30, paddingInline: 12 },
        outlined: { borderColor: brand.control },
      },
    },
    MuiIconButton: {
      styleOverrides: { root: { borderRadius: 999 } },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { backgroundImage: 'none' },
        outlined: { borderColor: brand.border },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, borderRadius: 999 },
        sizeSmall: { height: 24, fontSize: '0.75rem' },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: brand.rule, paddingTop: 14, paddingBottom: 14 },
        head: { color: brand.faint, fontSize: '0.75rem', fontWeight: 600, paddingTop: 10, paddingBottom: 10 },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { borderRadius: 999, height: 8, backgroundColor: brand.blueTint },
        bar: { borderRadius: 999, backgroundColor: brand.blue },
      },
    },
    MuiCheckbox: {
      styleOverrides: { root: { '&.Mui-checked': { color: brand.blue } } },
    },
    MuiDialog: {
      styleOverrides: { paper: { borderRadius: 16 } },
    },
    MuiAlert: {
      styleOverrides: { root: { borderRadius: 12 } },
    },
    MuiLink: {
      defaultProps: { underline: 'hover' },
    },
  },
})
