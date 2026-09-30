import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from processing_service.domain import ModelReference, Operation, Stage
from processing_service.messaging.events import (
    EVENT_TYPES,
    Artifacts,
    OutgoingEvent,
    ProcessingCompletedData,
    ProcessingFailedData,
    ProcessingProgressedData,
    ProcessingRequested,
    ProcessingStartedData,
)
from support import make_request

IDENTITY = {"job_id": uuid4(), "video_id": uuid4(), "attempt": 2}
MODEL = ModelReference(purpose=Operation.TRANSCRIPTION, provider="groq", model="m", version="v")

OUTGOING = [
    ProcessingStartedData(**IDENTITY, worker_id="worker-1"),
    ProcessingProgressedData(**IDENTITY, stage=Stage.TRANSCRIBING, progress_percent=25),
    ProcessingProgressedData(
        **IDENTITY, stage=Stage.SUMMARIZING, progress_percent=60, message="Resumindo"
    ),
    ProcessingCompletedData(
        **IDENTITY, artifacts=Artifacts(transcript_json_key="a/transcript.json"), models=(MODEL,)
    ),
    ProcessingCompletedData(
        **IDENTITY,
        artifacts=Artifacts(
            transcript_json_key="a/transcript.json",
            transcript_txt_key="a/transcript.txt",
            transcript_srt_key="a/transcript.srt",
            summary_json_key="a/summary.json",
            chapters_json_key="a/chapters.json",
        ),
        models=(MODEL,),
    ),
    ProcessingFailedData(
        **IDENTITY,
        stage=Stage.DOWNLOADING,
        error_code="video_not_found",
        error_message="Vídeo não encontrado",
        retryable=False,
    ),
]


def test_requested_example_matches_contract(validate_event):
    validate_event(make_request().model_dump(mode="json"))


def test_requested_rejects_duplicate_operations():
    with pytest.raises(ValidationError):
        make_request(operations=("summary", "summary"))


def test_requested_rejects_fields_outside_contract():
    payload = make_request().model_dump(mode="json")
    payload["data"]["priority"] = "high"

    with pytest.raises(ValidationError):
        ProcessingRequested.model_validate(payload)


def test_requested_rejects_other_event_types():
    payload = make_request().model_dump(mode="json")
    payload["event_type"] = "processing.started"

    with pytest.raises(ValidationError):
        ProcessingRequested.model_validate(payload)


@pytest.mark.parametrize("data", OUTGOING, ids=lambda data: type(data).__name__)
def test_outgoing_events_match_contract(data, validate_event):
    correlation_id = uuid4()
    payload = json.loads(OutgoingEvent.of(data, correlation_id=correlation_id).to_json())

    validate_event(payload)
    assert payload["event_type"] == EVENT_TYPES[type(data)]
    assert payload["correlation_id"] == str(correlation_id)
    assert payload["event_version"] == 1


def test_absent_optional_fields_are_omitted_instead_of_null():
    event = OutgoingEvent.of(OUTGOING[3], correlation_id=uuid4())

    artifacts = json.loads(event.to_json())["data"]["artifacts"]

    assert artifacts == {"transcript_json_key": "a/transcript.json"}


def test_every_event_gets_a_new_id():
    first = OutgoingEvent.of(OUTGOING[0], correlation_id=uuid4())
    second = OutgoingEvent.of(OUTGOING[0], correlation_id=uuid4())

    assert first.event_id != second.event_id
