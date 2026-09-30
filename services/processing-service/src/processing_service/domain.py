from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Operation(StrEnum):
    TRANSCRIPTION = "transcription"
    SUMMARY = "summary"
    CHAPTERS = "chapters"


class Stage(StrEnum):
    DOWNLOADING = "downloading"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    CREATING_CHAPTERS = "creating_chapters"
    UPLOADING_ARTIFACTS = "uploading_artifacts"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelReference(FrozenModel):
    purpose: Operation
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    version: str = Field(min_length=1)


class TranscriptSegment(FrozenModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    text: str


class Transcript(FrozenModel):
    language: str
    duration_seconds: float = Field(ge=0)
    segments: tuple[TranscriptSegment, ...]


class ConfigurationError(Exception):
    pass


class ProcessingError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
