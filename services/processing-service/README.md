# Processing Service

Worker Python responsável pelo pipeline de mídia e IA.

## Módulos

- `media`: download temporário, FFmpeg, normalização e limpeza.
- `transcription`: Speech-to-Text, timestamps e exportação TXT/SRT.
- `content_intelligence`: resumo, tópicos e capítulos.
- `messaging`: consumo idempotente e publicação de eventos.

O serviço não expõe API pública nem altera os bancos de Video Service ou Job
Service. Os artefatos são gravados no armazenamento de objetos e o estado é
comunicado por eventos.
