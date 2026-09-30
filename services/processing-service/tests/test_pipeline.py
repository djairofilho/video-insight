import json

import pytest

from processing_service.content_intelligence.models import ChapterList, Summary
from processing_service.domain import Operation, ProcessingError, Stage, Transcript
from processing_service.media.ffmpeg import MediaInfo
from processing_service.messaging.events import Artifacts, OutgoingEvent, ProcessingCompletedData
from processing_service.pipeline import ProcessingPipeline
from processing_service.storage import ArtifactKeys
from support import (
    FakeChapterWriter,
    FakeMedia,
    FakeSummarizer,
    FakeTranscriber,
    InMemoryStorage,
    RaisingStep,
    make_request,
)

VIDEO = b"conteudo-do-video"


def build(settings, storage, **overrides) -> ProcessingPipeline:
    parts = {
        "media": FakeMedia(),
        "transcriber": FakeTranscriber(),
        "summarizer": FakeSummarizer(),
        "chapter_writer": FakeChapterWriter(),
    }
    parts.update(overrides)
    return ProcessingPipeline(settings=settings, storage=storage, **parts)


def run(pipeline: ProcessingPipeline, request) -> list[OutgoingEvent]:
    events: list[OutgoingEvent] = []
    pipeline.run(request, events.append)
    return events


def storage_with_video(settings, request) -> InMemoryStorage:
    storage = InMemoryStorage()
    storage.objects[(settings.videos_bucket, request.data.storage_key)] = VIDEO
    return storage


def artifact(storage, settings, key) -> bytes:
    return storage.objects[(settings.artifacts_bucket, key)]


def test_full_run_publishes_every_stage_and_stores_artifacts(settings, validate_event):
    request = make_request()
    storage = storage_with_video(settings, request)

    events = run(build(settings, storage), request)

    assert [event.event_type for event in events] == (
        ["processing.started"] + ["processing.progressed"] * 6 + ["processing.completed"]
    )
    progressed = [event.data for event in events[1:-1]]
    assert [data.stage for data in progressed] == list(Stage)
    percents = [data.progress_percent for data in progressed]
    assert percents == sorted(set(percents))
    for event in events:
        validate_event(json.loads(event.to_json()))
        assert event.correlation_id == request.correlation_id
    assert events[0].data.worker_id == "worker-test"

    keys = ArtifactKeys.for_attempt(request.data.job_id, request.data.attempt)
    completed = events[-1].data
    assert completed.artifacts == Artifacts(
        transcript_json_key=keys.transcript_json,
        transcript_txt_key=keys.transcript_txt,
        transcript_srt_key=keys.transcript_srt,
        summary_json_key=keys.summary_json,
        chapters_json_key=keys.chapters_json,
    )
    assert [model.purpose for model in completed.models] == list(Operation)
    transcript = Transcript.model_validate_json(artifact(storage, settings, keys.transcript_json))
    assert transcript.duration_seconds == 95.0
    assert Summary.model_validate_json(artifact(storage, settings, keys.summary_json))
    assert ChapterList.model_validate_json(artifact(storage, settings, keys.chapters_json)).chapters
    assert artifact(storage, settings, keys.transcript_srt).startswith(b"1\n00:00:00,000 --> ")
    assert artifact(storage, settings, keys.transcript_txt).startswith(b"[00:00:00] Trecho 1.")
    manifest = artifact(storage, settings, keys.manifest)
    assert ProcessingCompletedData.model_validate_json(manifest) == completed


def test_transcription_only_skips_content_stages(settings):
    request = make_request(operations=("transcription",))
    storage = storage_with_video(settings, request)

    events = run(build(settings, storage), request)

    stages = [event.data.stage for event in events if event.event_type == "processing.progressed"]
    assert Stage.SUMMARIZING not in stages
    assert Stage.CREATING_CHAPTERS not in stages
    completed = events[-1].data
    assert completed.artifacts.summary_json_key is None
    assert completed.artifacts.chapters_json_key is None
    assert [model.purpose for model in completed.models] == [Operation.TRANSCRIPTION]


def test_summary_request_still_produces_the_required_transcript(settings):
    request = make_request(operations=("summary",))
    storage = storage_with_video(settings, request)

    completed = run(build(settings, storage), request)[-1].data

    assert completed.artifacts.transcript_json_key
    assert completed.artifacts.summary_json_key
    assert completed.artifacts.chapters_json_key is None


def test_redelivery_republishes_result_without_reprocessing(settings):
    request = make_request()
    storage = storage_with_video(settings, request)
    first = run(build(settings, storage), request)
    media = FakeMedia()

    second = run(build(settings, storage, media=media), request)

    assert [event.event_type for event in second] == ["processing.completed"]
    assert second[0].data == first[-1].data
    assert media.touched == []


def test_new_attempt_is_processed_again(settings):
    first_request = make_request(attempt=1)
    storage = storage_with_video(settings, first_request)
    run(build(settings, storage), first_request)
    retry = make_request(attempt=2, job_id=str(first_request.data.job_id))
    storage.objects[(settings.videos_bucket, retry.data.storage_key)] = VIDEO

    events = run(build(settings, storage), retry)

    assert events[0].event_type == "processing.started"
    assert events[-1].data.artifacts.transcript_json_key.endswith("attempt-2/transcript.json")


@pytest.mark.parametrize(
    ("info", "code"),
    [
        (MediaInfo(duration_seconds=600.5, has_audio=True), "video_too_long"),
        (MediaInfo(duration_seconds=60.0, has_audio=False), "no_audio_track"),
    ],
)
def test_invalid_media_fails_without_retry(settings, info, code):
    request = make_request()
    storage = storage_with_video(settings, request)

    failed = run(build(settings, storage, media=FakeMedia(info)), request)[-1]

    assert failed.event_type == "processing.failed"
    assert failed.data.stage == Stage.EXTRACTING_AUDIO
    assert failed.data.error_code == code
    assert failed.data.retryable is False
    assert not any(bucket == settings.artifacts_bucket for bucket, _ in storage.objects)


def test_oversized_video_fails_while_downloading(settings):
    limited = settings.model_copy(update={"max_video_size_bytes": 4})
    request = make_request()
    storage = storage_with_video(limited, request)

    failed = run(build(limited, storage), request)[-1].data

    assert (failed.stage, failed.error_code, failed.retryable) == (
        Stage.DOWNLOADING,
        "video_too_large",
        False,
    )


def test_missing_video_fails_while_downloading(settings):
    failed = run(build(settings, InMemoryStorage()), make_request())[-1].data

    assert (failed.stage, failed.error_code, failed.retryable) == (
        Stage.DOWNLOADING,
        "video_not_found",
        False,
    )


def test_summary_failure_keeps_the_transcript(settings):
    request = make_request()
    storage = storage_with_video(settings, request)
    summarizer = RaisingStep(
        ProcessingError("llm_unavailable", "Provedor fora do ar", retryable=True), Operation.SUMMARY
    )

    failed = run(build(settings, storage, summarizer=summarizer), request)[-1].data

    keys = ArtifactKeys.for_attempt(request.data.job_id, request.data.attempt)
    assert (failed.stage, failed.error_code, failed.retryable) == (
        Stage.SUMMARIZING,
        "llm_unavailable",
        True,
    )
    assert (settings.artifacts_bucket, keys.transcript_json) in storage.objects
    assert (settings.artifacts_bucket, keys.manifest) not in storage.objects


@pytest.mark.parametrize(
    ("error", "code", "message"),
    [
        (RuntimeError("boom"), "internal_error", "boom"),
        (RuntimeError(), "internal_error", "RuntimeError"),
        (ProcessingError("llm_refused", "   ", retryable=False), "llm_refused", "llm_refused"),
    ],
)
def test_failure_messages_are_never_empty(settings, error, code, message):
    request = make_request()
    storage = storage_with_video(settings, request)
    writer = RaisingStep(error, Operation.CHAPTERS)

    failed = run(build(settings, storage, chapter_writer=writer), request)[-1].data

    assert failed.stage == Stage.CREATING_CHAPTERS
    assert (failed.error_code, failed.error_message) == (code, message)


def test_long_failure_messages_are_truncated(settings):
    request = make_request()
    storage = storage_with_video(settings, request)
    transcriber = RaisingStep(
        ProcessingError("stt_error", "x" * 5000, retryable=True), Operation.TRANSCRIPTION
    )

    failed = run(build(settings, storage, transcriber=transcriber), request)[-1].data

    assert failed.stage == Stage.TRANSCRIBING
    assert len(failed.error_message) == 2000


def test_temporary_files_are_removed(settings):
    request = make_request()
    storage = storage_with_video(settings, request)
    media = FakeMedia()

    run(build(settings, storage, media=media), request)

    assert media.touched
    assert all(not path.exists() and not path.parent.exists() for path in media.touched)
