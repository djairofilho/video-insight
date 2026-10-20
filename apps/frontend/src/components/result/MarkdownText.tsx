import { Box, Link, Typography } from '@mui/material'
import ReactMarkdown, { type Components } from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'

// Subtítulos do Markdown no tamanho do texto, em azul e negrito: ficam abaixo do título do painel e acima dos parágrafos.
const heading = { mt: 3, mb: 1, fontSize: '1rem', fontWeight: 700, color: '#0052cc' } as const

const blockComponents: Components = {
  h1: ({ children }) => <Typography component="h3" sx={heading}>{children}</Typography>,
  h2: ({ children }) => <Typography component="h3" sx={heading}>{children}</Typography>,
  h3: ({ children }) => <Typography variant="h4" component="h4" sx={{ mt: 2.5, mb: 1 }}>{children}</Typography>,
  h4: ({ children }) => <Typography variant="h4" component="h4" sx={{ mt: 2, mb: 1 }}>{children}</Typography>,
  p: ({ children }) => <Typography sx={{ mb: 1.5 }}>{children}</Typography>,
  ul: ({ children }) => <Box component="ul" sx={{ pl: 3, my: 1.5, '& li': { mb: 1, lineHeight: 1.65 } }}>{children}</Box>,
  ol: ({ children }) => <Box component="ol" sx={{ pl: 3, my: 1.5, '& li': { mb: 1, lineHeight: 1.65 } }}>{children}</Box>,
  a: ({ children, href }) => (
    <Link href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </Link>
  ),
  strong: ({ children }) => <Box component="strong" sx={{ fontWeight: 650, color: 'text.primary' }}>{children}</Box>,
}

const inlineComponents: Components = {
  ...blockComponents,
  p: ({ children }) => <>{children}</>,
}

interface MarkdownTextProps {
  children: string
  /** Renderiza sem parágrafos, para textos curtos dentro de outro elemento. */
  inline?: boolean
}

/** Markdown gerado pela IA, sanitizado: HTML bruto é descartado e links abrem em nova aba. */
export function MarkdownText({ children, inline = false }: MarkdownTextProps) {
  return (
    <ReactMarkdown rehypePlugins={[rehypeSanitize]} components={inline ? inlineComponents : blockComponents}>
      {children}
    </ReactMarkdown>
  )
}
