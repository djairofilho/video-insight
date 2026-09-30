import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from processing_service.domain import (
    ModelReference,
    Operation,
    ProcessingError,
    Transcript,
    TranscriptSegment,
)

_RETRYABLE_STATUS = {408, 409, 429}
_ERROR_DETAIL = 300


class GroqTranscriber:
    def __init__(
        self,
        client: httpx.Client,
        *,
        model: str,
        language: str,
        max_attempts: int,
        max_retry_wait_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._model = model
        self._language = language
        self._max_attempts = max_attempts
        self._max_retry_wait = max_retry_wait_seconds
        self._sleep = sleep
        self.model = ModelReference(
            purpose=Operation.TRANSCRIPTION, provider="groq", model=model, version=model
        )

    @classmethod
    def create(
        cls,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
        model: str,
        language: str,
        max_attempts: int,
        max_retry_wait_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> "GroqTranscriber":
        client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )
        return cls(
            client,
            model=model,
            language=language,
            max_attempts=max_attempts,
            max_retry_wait_seconds=max_retry_wait_seconds,
        )

    def transcribe(self, audio: Path, *, duration_seconds: float) -> Transcript:
        body = self._request(audio)
        segments = tuple(
            segment
            for raw in body.get("segments") or ()
            if (segment := _segment(raw, duration_seconds)) is not None
        )
        return Transcript(
            language=self._language, duration_seconds=duration_seconds, segments=segments
        )

    def _request(self, audio: Path) -> dict[str, Any]:
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._post(audio)
            except httpx.TransportError as error:
                failure = ProcessingError(
                    "transcription_unavailable", f"Falha de rede com a Groq: {error}", retryable=True
                )
                wait = 2.0**attempt
            else:
                if response.is_success:
                    return response.json()
                detail = response.text[:_ERROR_DETAIL]
                message = f"Groq respondeu {response.status_code}: {detail}"
                if response.status_code not in _RETRYABLE_STATUS and response.status_code < 500:
                    raise ProcessingError("transcription_rejected", message, retryable=False)
                failure = ProcessingError("transcription_unavailable", message, retryable=True)
                wait = _retry_after(response) or 2.0**attempt
            if attempt == self._max_attempts:
                raise failure
            self._sleep(min(wait, self._max_retry_wait))
        raise AssertionError("unreachable")

    def _post(self, audio: Path) -> httpx.Response:
        with audio.open("rb") as file:
            return self._client.post(
                "/audio/transcriptions",
                files={"file": (audio.name, file, "audio/flac")},
                data={
                    "model": self._model,
                    "language": self._language,
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "segment",
                    "temperature": "0",
                },
            )


def _segment(raw: dict[str, Any], duration_seconds: float) -> TranscriptSegment | None:
    text = str(raw.get("text") or "").strip()
    if not text:
        return None
    start = min(max(float(raw["start"]), 0.0), duration_seconds)
    end = min(max(float(raw["end"]), start), duration_seconds)
    return TranscriptSegment(start_seconds=start, end_seconds=end, text=text)


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return float(response.headers["retry-after"])
    except (KeyError, ValueError):
        return None
