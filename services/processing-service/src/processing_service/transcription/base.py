from pathlib import Path
from typing import Protocol

from processing_service.domain import ModelReference, Transcript


class Transcriber(Protocol):
    @property
    def model(self) -> ModelReference: ...

    def transcribe(self, audio: Path, *, duration_seconds: float) -> Transcript: ...
