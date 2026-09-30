from pathlib import Path
from uuid import uuid4

import docker
import pytest

from processing_service.content_intelligence.models import Chapter, ParagraphBlock, Summary
from processing_service.domain import (
    ModelReference,
    Operation,
    ProcessingError,
    Transcript,
    TranscriptSegment,
)
from processing_service.media.ffmpeg import MediaInfo
from processing_service.messaging.events import ProcessingRequested


def make_request(
    *,
    operations: tuple[str, ...] = ("transcription", "summary", "chapters"),
    attempt: int = 1,
    job_id: str | None = None,
    storage_key: str = "uploads/video.mp4",
) -> ProcessingRequested:
    return ProcessingRequested.model_validate(
        {
            "event_id": str(uuid4()),
            "event_type": "processing.requested",
            "event_version": 1,
            "occurred_at": "2026-09-30T12:00:00Z",
            "correlation_id": str(uuid4()),
            "data": {
                "job_id": job_id or str(uuid4()),
                "video_id": str(uuid4()),
                "storage_key": storage_key,
                "operations": list(operations),
                "attempt": attempt,
            },
        }
    )


class FakeTranscriber:
    model = ModelReference(
        purpose=Operation.TRANSCRIPTION, provider="fake", model="fake-transcriber", version="1"
    )

    def transcribe(self, audio: Path, *, duration_seconds: float) -> Transcript:
        segments = tuple(
            TranscriptSegment(
                start_seconds=float(start),
                end_seconds=min(start + 10.0, duration_seconds),
                text=f"Trecho {index}.",
            )
            for index, start in enumerate(range(0, int(duration_seconds), 10), start=1)
        )
        return Transcript(language="pt", duration_seconds=duration_seconds, segments=segments)


class FakeSummarizer:
    model = ModelReference(
        purpose=Operation.SUMMARY, provider="fake", model="fake-summarizer", version="1"
    )

    def summarize(self, transcript: Transcript) -> Summary:
        return Summary(content_kind="lecture", text="Resumo do vídeo.")


class FakeChapterWriter:
    model = ModelReference(
        purpose=Operation.CHAPTERS, provider="fake", model="fake-chapter-writer", version="1"
    )

    def write_chapters(self, transcript: Transcript) -> tuple[Chapter, ...]:
        return (
            Chapter(
                title="Introdução",
                start_seconds=0.0,
                end_seconds=transcript.duration_seconds,
                blocks=(ParagraphBlock(text="Texto do capítulo."),),
            ),
        )


class RaisingStep:
    def __init__(self, error: Exception, purpose: Operation) -> None:
        self.error = error
        self.model = ModelReference(purpose=purpose, provider="fake", model="raising", version="1")

    def transcribe(self, audio: Path, *, duration_seconds: float) -> Transcript:
        raise self.error

    def summarize(self, transcript: Transcript) -> Summary:
        raise self.error

    def write_chapters(self, transcript: Transcript) -> tuple[Chapter, ...]:
        raise self.error


class InMemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def download(self, bucket: str, key: str, destination: Path) -> None:
        try:
            destination.write_bytes(self.objects[(bucket, key)])
        except KeyError as error:
            raise ProcessingError("video_not_found", key, retryable=False) from error

    def upload(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self.objects[(bucket, key)] = data

    def read(self, bucket: str, key: str) -> bytes | None:
        return self.objects.get((bucket, key))


class FakeMedia:
    def __init__(self, info: MediaInfo | None = None) -> None:
        self.info = info or MediaInfo(duration_seconds=95.0, has_audio=True)
        self.touched: list[Path] = []

    def probe(self, video: Path) -> MediaInfo:
        self.touched.append(video)
        return self.info

    def extract_audio(self, video: Path, destination: Path) -> Path:
        destination.write_bytes(b"audio")
        self.touched.append(destination)
        return destination


def _docker_available() -> bool:
    try:
        return bool(docker.from_env().ping())
    except Exception:
        return False


requires_docker = pytest.mark.skipif(not _docker_available(), reason="Docker indisponível")
