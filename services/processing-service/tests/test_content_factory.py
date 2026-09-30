import pytest
from pydantic import SecretStr

from processing_service.content_intelligence.chapter_agent import AgentChapterWriter
from processing_service.content_intelligence.factory import create_content_writers
from processing_service.content_intelligence.summary_agent import AgentSummarizer
from processing_service.domain import ConfigurationError, Operation


def test_builds_gemini_agents_from_settings(settings):
    configured = settings.model_copy(update={"gemini_api_key": SecretStr("chave")})

    summarizer, chapter_writer = create_content_writers(configured)

    assert isinstance(summarizer, AgentSummarizer)
    assert isinstance(chapter_writer, AgentChapterWriter)
    assert (summarizer.model.provider, summarizer.model.model) == ("google", "gemini-3.5-flash-lite")
    assert chapter_writer.model.purpose == Operation.CHAPTERS


def test_requires_gemini_api_key(settings):
    with pytest.raises(ConfigurationError, match="GEMINI_API_KEY"):
        create_content_writers(settings.model_copy(update={"gemini_api_key": SecretStr("")}))


def test_rejects_unknown_provider(settings):
    with pytest.raises(ConfigurationError, match="desconhecido"):
        create_content_writers(settings.model_copy(update={"content_provider": "outro"}))
