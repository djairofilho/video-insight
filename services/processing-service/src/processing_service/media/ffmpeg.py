import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from processing_service.domain import ProcessingError

Runner = Callable[..., subprocess.CompletedProcess[str]]

_STDERR_TAIL = 500


@dataclass(frozen=True)
class MediaInfo:
    duration_seconds: float
    has_audio: bool


class MediaToolkit(Protocol):
    def probe(self, video: Path) -> MediaInfo: ...

    def extract_audio(self, video: Path, destination: Path) -> Path: ...


class FfmpegMedia:
    def __init__(self, timeout_seconds: float, run: Runner = subprocess.run) -> None:
        self._timeout = timeout_seconds
        self._run = run

    def probe(self, video: Path) -> MediaInfo:
        output = self._execute(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration:stream=codec_type",
                "-of", "json", str(video),
            ],
            error_code="invalid_media",
        )
        try:
            info = json.loads(output)
            duration = float(info["format"]["duration"])
        except (ValueError, KeyError, TypeError) as error:
            raise ProcessingError(
                "invalid_media", "Não foi possível ler a duração do vídeo", retryable=False
            ) from error
        streams = info.get("streams", [])
        has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
        return MediaInfo(duration_seconds=duration, has_audio=has_audio)

    def extract_audio(self, video: Path, destination: Path) -> Path:
        self._execute(
            [
                "ffmpeg", "-nostdin", "-v", "error", "-y",
                "-i", str(video),
                "-vn", "-ac", "1", "-ar", "16000",
                "-c:a", "flac",
                str(destination),
            ],
            error_code="audio_extraction_failed",
        )
        return destination

    def _execute(self, command: Sequence[str], *, error_code: str) -> str:
        try:
            result = self._run(
                list(command), capture_output=True, text=True, timeout=self._timeout, check=False
            )
        except FileNotFoundError as error:
            raise ProcessingError(
                "ffmpeg_unavailable", f"{command[0]} não está instalado", retryable=True
            ) from error
        except subprocess.TimeoutExpired as error:
            raise ProcessingError(
                "media_timeout", f"{command[0]} excedeu {self._timeout:g}s", retryable=True
            ) from error
        if result.returncode != 0:
            detail = (result.stderr or "").strip()[-_STDERR_TAIL:] or f"código {result.returncode}"
            raise ProcessingError(error_code, detail, retryable=False)
        return result.stdout
