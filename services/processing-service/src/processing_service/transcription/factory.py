from collections.abc import Callable

from processing_service.config import Settings
from processing_service.domain import ConfigurationError
from processing_service.transcription.base import Transcriber
from processing_service.transcription.groq import GroqTranscriber


def _groq(settings: Settings) -> Transcriber:
    api_key = settings.groq_api_key.get_secret_value()
    if not api_key:
        raise ConfigurationError("GROQ_API_KEY não foi definido")
    return GroqTranscriber.create(
        api_key=api_key,
        base_url=settings.groq_base_url,
        timeout_seconds=settings.groq_timeout_seconds,
        model=settings.groq_model,
        language=settings.transcription_language,
        max_attempts=settings.groq_max_attempts,
        max_retry_wait_seconds=settings.groq_max_retry_wait_seconds,
    )


_PROVIDERS: dict[str, Callable[[Settings], Transcriber]] = {"groq": _groq}


def create_transcriber(settings: Settings) -> Transcriber:
    try:
        build = _PROVIDERS[settings.transcription_provider]
    except KeyError as error:
        raise ConfigurationError(
            f"Provedor de transcrição desconhecido: {settings.transcription_provider}"
        ) from error
    return build(settings)
