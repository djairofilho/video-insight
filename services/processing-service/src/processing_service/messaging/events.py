from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from processing_service.domain import ModelReference, Operation, Stage

EVENT_VERSION = 1


class EventData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: UUID
    video_id: UUID
    attempt: int = Field(ge=1)


class ProcessingRequestedData(EventData):
    storage_key: str = Field(min_length=1)
    operations: tuple[Operation, ...] = Field(min_length=1)

    @field_validator("operations")
    @classmethod
    def reject_duplicates(cls, operations: tuple[Operation, ...]) -> tuple[Operation, ...]:
        if len(set(operations)) != len(operations):
            raise ValueError("operations não pode repetir itens")
        return operations


class ProcessingRequested(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: UUID
    event_type: Literal["processing.requested"]
    event_version: Literal[1]
    occurred_at: datetime
    correlation_id: UUID
    data: ProcessingRequestedData


class ProcessingStartedData(EventData):
    worker_id: str = Field(min_length=1)


class ProcessingProgressedData(EventData):
    stage: Stage
    progress_percent: int = Field(ge=0, le=100)
    message: str | None = Field(default=None, max_length=500)


class Artifacts(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    transcript_json_key: str = Field(min_length=1)
    transcript_txt_key: str | None = Field(default=None, min_length=1)
    transcript_srt_key: str | None = Field(default=None, min_length=1)
    summary_json_key: str | None = Field(default=None, min_length=1)
    chapters_json_key: str | None = Field(default=None, min_length=1)


class ProcessingCompletedData(EventData):
    artifacts: Artifacts
    models: tuple[ModelReference, ...]


class ProcessingFailedData(EventData):
    stage: Stage
    error_code: str = Field(min_length=1)
    error_message: str = Field(min_length=1, max_length=2000)
    retryable: bool


OutgoingData = (
    ProcessingStartedData
    | ProcessingProgressedData
    | ProcessingCompletedData
    | ProcessingFailedData
)

EVENT_TYPES: dict[type[BaseModel], str] = {
    ProcessingStartedData: "processing.started",
    ProcessingProgressedData: "processing.progressed",
    ProcessingCompletedData: "processing.completed",
    ProcessingFailedData: "processing.failed",
}


class OutgoingEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: int = EVENT_VERSION
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: UUID
    data: OutgoingData

    @classmethod
    def of(cls, data: OutgoingData, *, correlation_id: UUID) -> "OutgoingEvent":
        return cls(event_type=EVENT_TYPES[type(data)], correlation_id=correlation_id, data=data)

    def to_json(self) -> bytes:
        return self.model_dump_json(exclude_none=True).encode()


EventSink = Callable[[OutgoingEvent], None]
