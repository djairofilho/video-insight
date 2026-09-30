from typing import Protocol

from processing_service.content_intelligence.models import Chapter, Summary
from processing_service.domain import ModelReference, Transcript


class Summarizer(Protocol):
    @property
    def model(self) -> ModelReference: ...

    def summarize(self, transcript: Transcript) -> Summary: ...


class ChapterWriter(Protocol):
    @property
    def model(self) -> ModelReference: ...

    def write_chapters(self, transcript: Transcript) -> tuple[Chapter, ...]: ...
