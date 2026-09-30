from uuid import uuid4

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
