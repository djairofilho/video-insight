from collections.abc import Callable

from processing_service.config import Settings
from processing_service.content_intelligence.agent import AgentLimits, AgentRunner
from processing_service.content_intelligence.base import ChapterWriter, Summarizer
from processing_service.content_intelligence.chapter_agent import AgentChapterWriter
from processing_service.content_intelligence.gemini import GeminiChatModel
from processing_service.content_intelligence.summary_agent import AgentSummarizer
from processing_service.domain import ConfigurationError

ContentWriters = tuple[Summarizer, ChapterWriter]


def _gemini(settings: Settings) -> ContentWriters:
    api_key = settings.gemini_api_key.get_secret_value()
    if not api_key:
        raise ConfigurationError("GEMINI_API_KEY não foi definido")
    chat = GeminiChatModel.create(
        api_key=api_key,
        model=settings.gemini_model,
        fallback_model=settings.gemini_fallback_model or None,
        thinking_level=settings.gemini_thinking_level,
        timeout_seconds=settings.gemini_timeout_seconds,
        call_attempts=settings.gemini_call_attempts,
        max_backoff_seconds=settings.gemini_max_backoff_seconds,
    )
    summary_limits = AgentLimits(
        max_turns=settings.summary_agent_max_turns,
        max_tool_calls=settings.summary_agent_max_tool_calls,
        max_nudges=settings.agent_max_nudges,
        wall_clock_seconds=settings.summary_agent_wall_clock_seconds,
    )
    chapter_limits = AgentLimits(
        max_turns=settings.chapter_agent_max_turns,
        max_tool_calls=settings.chapter_agent_max_tool_calls,
        max_nudges=settings.agent_max_nudges,
        wall_clock_seconds=settings.chapter_agent_wall_clock_seconds,
    )
    return (
        AgentSummarizer(AgentRunner(chat, summary_limits)),
        AgentChapterWriter(AgentRunner(chat, chapter_limits)),
    )


_PROVIDERS: dict[str, Callable[[Settings], ContentWriters]] = {"gemini": _gemini}


def create_content_writers(settings: Settings) -> ContentWriters:
    try:
        build = _PROVIDERS[settings.content_provider]
    except KeyError as error:
        raise ConfigurationError(
            f"Provedor de conteúdo desconhecido: {settings.content_provider}"
        ) from error
    return build(settings)
