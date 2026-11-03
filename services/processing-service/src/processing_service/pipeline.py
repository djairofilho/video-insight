import logging
import tempfile
import hashlib
import json
import time
from datetime import UTC, datetime
from threading import Lock
from collections.abc import Callable
from pathlib import Path

from processing_service.config import Settings
from processing_service.content_intelligence.base import ChapterWriter, Summarizer
from processing_service.content_intelligence.models import ChapterList
from processing_service.domain import ModelReference, Operation, ProcessingError, Stage, Transcript
from processing_service.content_intelligence.models import Summary
from processing_service.metrics import METRICS
from processing_service.media.ffmpeg import MediaToolkit
from processing_service.messaging.events import (
    Artifacts,
    EventData,
    EventSink,
    OutgoingData,
    OutgoingEvent,
    ProcessingCompletedData,
    ProcessingFailedData,
    ProcessingProgressedData,
    ProcessingRequested,
    ProcessingRequestedData,
    ProcessingStartedData,
)
from processing_service.storage import ArtifactKeys, ObjectStorage
from processing_service.transcription import exporters
from processing_service.transcription.base import Transcriber

logger = logging.getLogger(__name__)

PROGRESS_BY_STAGE = {
    Stage.DOWNLOADING: 5,
    Stage.EXTRACTING_AUDIO: 15,
    Stage.TRANSCRIBING: 25,
    Stage.SUMMARIZING: 60,
    Stage.CREATING_CHAPTERS: 75,
    Stage.UPLOADING_ARTIFACTS: 90,
}

_JSON = "application/json"
_MAX_ERROR_MESSAGE = 2000

_Publish = Callable[[OutgoingData], None]
# shortcut: coordena consumidores deste processo; adotar lease durável antes de replicar em outra máquina.
_JOB_LOCKS = tuple(Lock() for _ in range(64))


class ProcessingPipeline:
    def __init__(
        self,
        *,
        settings: Settings,
        storage: ObjectStorage,
        media: MediaToolkit,
        transcriber: Transcriber,
        summarizer: Summarizer,
        chapter_writer: ChapterWriter,
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._media = media
        self._transcriber = transcriber
        self._summarizer = summarizer
        self._chapter_writer = chapter_writer

    def run(self, request: ProcessingRequested, emit: EventSink) -> None:
        with _JOB_LOCKS[request.data.job_id.int % len(_JOB_LOCKS)]:
            self._run(request, emit)

    @METRICS.active.track_inprogress()
    @METRICS.duration.time()
    def _run(self, request: ProcessingRequested, emit: EventSink) -> None:
        data = request.data
        keys = ArtifactKeys.for_attempt(data.job_id, data.attempt)

        def publish(payload: OutgoingData) -> None:
            emit(OutgoingEvent.of(payload, correlation_id=request.correlation_id))

        previous = self._storage.read(self._settings.artifacts_bucket, keys.manifest)
        if previous is not None:
            METRICS.jobs.labels("replayed").inc()
            logger.info("Tentativa %s já concluída; republicando resultado", keys.prefix)
            publish(ProcessingCompletedData.model_validate_json(previous))
            return

        publish(ProcessingStartedData(**_identity(data), worker_id=self._settings.worker_id))
        occurred = request.occurred_at.replace(tzinfo=request.occurred_at.tzinfo or UTC)
        METRICS.queue_wait.observe(max(0, (datetime.now(UTC) - occurred).total_seconds()))
        tracker = _StageTracker(data, publish)
        try:
            with tempfile.TemporaryDirectory(prefix="video-insight-") as workdir:
                completed = self._process(data, keys, Path(workdir), tracker)
        except ProcessingError as error:
            METRICS.jobs.labels("failed").inc()
            logger.warning("Job %s falhou em %s: %s", data.job_id, tracker.stage, error.code)
            publish(_failure(data, tracker.stage, error.code, error.message, error.retryable))
            return
        except Exception as error:
            METRICS.jobs.labels("failed").inc()
            logger.exception("Erro inesperado no job %s", data.job_id)
            message = str(error) or type(error).__name__
            publish(_failure(data, tracker.stage, "internal_error", message, retryable=True))
            return
        finally:
            tracker.close()
        METRICS.jobs.labels("completed").inc()
        publish(completed)

    def _process(
        self,
        data: ProcessingRequestedData,
        keys: ArtifactKeys,
        workdir: Path,
        tracker: "_StageTracker",
    ) -> ProcessingCompletedData:
        tracker.enter(Stage.DOWNLOADING)
        video = workdir / "video.mp4"
        self._storage.download(self._settings.videos_bucket, data.storage_key, video)
        if video.stat().st_size > self._settings.max_video_size_bytes:
            raise ProcessingError(
                "video_too_large", "O vídeo excede o tamanho máximo do MVP", retryable=False
            )

        tracker.enter(Stage.EXTRACTING_AUDIO)
        info = self._media.probe(video)
        if info.duration_seconds > self._settings.max_video_duration_seconds:
            raise ProcessingError(
                "video_too_long", "O vídeo excede a duração máxima do MVP", retryable=False
            )
        if not info.has_audio:
            raise ProcessingError("no_audio_track", "O vídeo não tem trilha de áudio", retryable=False)
        with video.open("rb") as source:
            source_hash = hashlib.file_digest(source, "sha256").hexdigest()
        profile = {"source": source_hash, "video_id": str(data.video_id), "version": 1,
                   "config": self._settings.model_dump(mode="json", include={
                       "transcription_language", "groq_model", "gemini_model", "gemini_fallback_model",
                       "gemini_thinking_level", "gemini_max_output_tokens",
                       "summary_agent_max_turns", "chapter_agent_max_turns"})}
        fingerprint = hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()
        checkpoint = f"jobs/{data.job_id}/checkpoints/{fingerprint}"
        cached = self._read_checkpoint(f"{checkpoint}/transcript.json", Transcript)
        audio = None if cached else self._media.extract_audio(video, workdir / "audio.flac")

        tracker.enter(Stage.TRANSCRIBING)
        if cached:
            transcript, transcript_model = cached
            METRICS.checkpoints.labels("transcribing").inc()
        else:
            transcript = self._transcriber.transcribe(audio, duration_seconds=info.duration_seconds)
            transcript_model = self._transcriber.model
            self._write_checkpoint(f"{checkpoint}/transcript.json", transcript, transcript_model)
        self._upload(keys.transcript_json, exporters.to_json(transcript), _JSON)
        artifacts: dict[str, str] = {"transcript_json_key": keys.transcript_json}
        models: list[ModelReference] = [transcript_model]

        if Operation.SUMMARY in data.operations:
            tracker.enter(Stage.SUMMARIZING)
            cached_summary = self._read_checkpoint(f"{checkpoint}/summary.json", Summary)
            if cached_summary:
                summary, summary_model = cached_summary
                METRICS.checkpoints.labels("summarizing").inc()
            else:
                summary = self._summarizer.summarize(transcript)
                summary_model = self._summarizer.model
                self._write_checkpoint(f"{checkpoint}/summary.json", summary, summary_model)
            self._upload(keys.summary_json, summary.model_dump_json(indent=2).encode(), _JSON)
            artifacts["summary_json_key"] = keys.summary_json
            models.append(summary_model)

        if Operation.CHAPTERS in data.operations:
            tracker.enter(Stage.CREATING_CHAPTERS)
            cached_chapters = self._read_checkpoint(f"{checkpoint}/chapters.json", ChapterList)
            if cached_chapters:
                chapters, chapters_model = cached_chapters
                METRICS.checkpoints.labels("creating_chapters").inc()
            else:
                chapters = ChapterList(chapters=self._chapter_writer.write_chapters(transcript))
                chapters_model = self._chapter_writer.model
                self._write_checkpoint(f"{checkpoint}/chapters.json", chapters, chapters_model)
            self._upload(keys.chapters_json, chapters.model_dump_json(indent=2).encode(), _JSON)
            artifacts["chapters_json_key"] = keys.chapters_json
            models.append(chapters_model)

        tracker.enter(Stage.UPLOADING_ARTIFACTS)
        self._upload(keys.transcript_txt, exporters.to_txt(transcript), "text/plain; charset=utf-8")
        self._upload(keys.transcript_srt, exporters.to_srt(transcript), "application/x-subrip")
        artifacts["transcript_txt_key"] = keys.transcript_txt
        artifacts["transcript_srt_key"] = keys.transcript_srt

        completed = ProcessingCompletedData(
            **_identity(data), artifacts=Artifacts(**artifacts), models=tuple(models)
        )
        self._upload(keys.manifest, completed.model_dump_json().encode(), _JSON)
        METRICS.audio.inc(info.duration_seconds)
        return completed

    def _read_checkpoint(self, key, schema):
        content = self._storage.read(self._settings.artifacts_bucket, key)
        if content is None:
            return None
        try:
            checkpoint = json.loads(content)
            return schema.model_validate(checkpoint["value"]), ModelReference.model_validate(checkpoint["model"])
        except (ValueError, KeyError, TypeError) as error:
            raise ProcessingError("checkpoint_invalid", "Etapa persistida inválida.", retryable=False) from error

    def _write_checkpoint(self, key, value, model):
        payload = {"value": value.model_dump(mode="json"), "model": model.model_dump(mode="json")}
        self._upload(key, json.dumps(payload, ensure_ascii=False).encode(), _JSON)

    def _upload(self, key: str, content: bytes, content_type: str) -> None:
        self._storage.upload(self._settings.artifacts_bucket, key, content, content_type)


class _StageTracker:
    def __init__(self, data: ProcessingRequestedData, publish: _Publish) -> None:
        self._data = data
        self._publish = publish
        self.stage = Stage.DOWNLOADING
        self._started = None

    def enter(self, stage: Stage) -> None:
        self.close()
        self.stage = stage
        self._started = time.monotonic()
        self._publish(
            ProcessingProgressedData(
                **_identity(self._data), stage=stage, progress_percent=PROGRESS_BY_STAGE[stage]
            )
        )

    def close(self) -> None:
        if self._started is not None:
            METRICS.stages.labels(self.stage.value).observe(time.monotonic() - self._started)
            self._started = None


def _identity(data: EventData) -> dict[str, object]:
    return {"job_id": data.job_id, "video_id": data.video_id, "attempt": data.attempt}


def _failure(
    data: ProcessingRequestedData, stage: Stage, code: str, message: str, retryable: bool
) -> ProcessingFailedData:
    return ProcessingFailedData(
        **_identity(data),
        stage=stage,
        error_code=code,
        error_message=(message.strip() or code)[:_MAX_ERROR_MESSAGE],
        retryable=retryable,
    )
