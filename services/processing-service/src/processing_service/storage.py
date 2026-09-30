import io
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from minio import Minio
from minio.error import S3Error

from processing_service.config import Settings
from processing_service.domain import ConfigurationError, ProcessingError

_MISSING_CODES = {"NoSuchKey", "NoSuchBucket", "NoSuchObject"}


class ObjectStorage(Protocol):
    def download(self, bucket: str, key: str, destination: Path) -> None: ...

    def upload(self, bucket: str, key: str, data: bytes, content_type: str) -> None: ...

    def read(self, bucket: str, key: str) -> bytes | None: ...


@dataclass(frozen=True)
class ArtifactKeys:
    prefix: str

    @classmethod
    def for_attempt(cls, job_id: UUID, attempt: int) -> "ArtifactKeys":
        return cls(f"jobs/{job_id}/attempt-{attempt}")

    @property
    def transcript_json(self) -> str:
        return f"{self.prefix}/transcript.json"

    @property
    def transcript_txt(self) -> str:
        return f"{self.prefix}/transcript.txt"

    @property
    def transcript_srt(self) -> str:
        return f"{self.prefix}/transcript.srt"

    @property
    def summary_json(self) -> str:
        return f"{self.prefix}/summary.json"

    @property
    def chapters_json(self) -> str:
        return f"{self.prefix}/chapters.json"

    @property
    def manifest(self) -> str:
        return f"{self.prefix}/completed.json"


class MinioStorage:
    def __init__(self, client: Minio) -> None:
        self._client = client

    @classmethod
    def from_settings(cls, settings: Settings) -> "MinioStorage":
        secret_key = settings.minio_secret_key.get_secret_value()
        if not secret_key:
            raise ConfigurationError("MINIO_SECRET_KEY não foi definido")
        return cls(
            Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=secret_key,
                secure=settings.minio_secure,
            )
        )

    def download(self, bucket: str, key: str, destination: Path) -> None:
        try:
            self._client.fget_object(bucket, key, str(destination))
        except S3Error as error:
            if error.code in _MISSING_CODES:
                raise ProcessingError(
                    "video_not_found", f"Vídeo não encontrado: {bucket}/{key}", retryable=False
                ) from error
            raise ProcessingError("storage_error", str(error), retryable=True) from error

    def upload(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        try:
            self._put(bucket, key, data, content_type)
        except S3Error as error:
            if error.code != "NoSuchBucket":
                raise
            self._client.make_bucket(bucket)
            self._put(bucket, key, data, content_type)

    def _put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(bucket, key, io.BytesIO(data), len(data), content_type=content_type)

    def read(self, bucket: str, key: str) -> bytes | None:
        try:
            response = self._client.get_object(bucket, key)
        except S3Error as error:
            if error.code in _MISSING_CODES:
                return None
            raise
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
