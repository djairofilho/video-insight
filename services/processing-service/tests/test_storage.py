from unittest.mock import MagicMock
from uuid import UUID

import pytest
from minio.error import S3Error
from pydantic import SecretStr

from processing_service.domain import ProcessingError
from processing_service.storage import ArtifactKeys, MinioStorage
from support import requires_docker

MINIO_IMAGE = "cgr.dev/chainguard/minio:latest"


def s3_error(code: str) -> S3Error:
    return S3Error(MagicMock(), code, "mensagem", "recurso", "requisicao", "host")


def test_artifact_keys_are_deterministic_per_attempt():
    job_id = UUID("7b2f3c1e-0d4a-4c5e-9f6b-2a1d3e4f5a6b")

    keys = ArtifactKeys.for_attempt(job_id, 2)

    prefix = f"jobs/{job_id}/attempt-2"
    assert keys.transcript_json == f"{prefix}/transcript.json"
    assert [keys.transcript_txt, keys.transcript_srt, keys.summary_json] == [
        f"{prefix}/transcript.txt",
        f"{prefix}/transcript.srt",
        f"{prefix}/summary.json",
    ]
    assert keys.chapters_json == f"{prefix}/chapters.json"
    assert keys.manifest == f"{prefix}/completed.json"


def test_download_writes_to_destination(tmp_path):
    client = MagicMock()

    MinioStorage(client).download("videos", "uploads/v.mp4", tmp_path / "v.mp4")

    client.fget_object.assert_called_once_with("videos", "uploads/v.mp4", str(tmp_path / "v.mp4"))


@pytest.mark.parametrize(
    ("code", "expected", "retryable"),
    [("NoSuchKey", "video_not_found", False), ("InternalError", "storage_error", True)],
)
def test_download_errors_become_processing_errors(tmp_path, code, expected, retryable):
    client = MagicMock()
    client.fget_object.side_effect = s3_error(code)

    with pytest.raises(ProcessingError) as raised:
        MinioStorage(client).download("videos", "k", tmp_path / "v.mp4")

    assert (raised.value.code, raised.value.retryable) == (expected, retryable)


def test_upload_creates_missing_bucket_and_retries():
    client = MagicMock()
    client.put_object.side_effect = [s3_error("NoSuchBucket"), None]

    MinioStorage(client).upload("artifacts", "a.json", b"{}", "application/json")

    client.make_bucket.assert_called_once_with("artifacts")
    assert client.put_object.call_count == 2
    assert client.put_object.call_args.kwargs["content_type"] == "application/json"


def test_upload_propagates_other_errors():
    client = MagicMock()
    client.put_object.side_effect = s3_error("AccessDenied")

    with pytest.raises(S3Error):
        MinioStorage(client).upload("artifacts", "a.json", b"{}", "application/json")
    client.make_bucket.assert_not_called()


def test_read_returns_content_and_releases_connection():
    client = MagicMock()
    response = client.get_object.return_value
    response.read.return_value = b"conteudo"

    assert MinioStorage(client).read("artifacts", "a.json") == b"conteudo"
    response.close.assert_called_once()
    response.release_conn.assert_called_once()


def test_read_missing_object_returns_none():
    client = MagicMock()
    client.get_object.side_effect = s3_error("NoSuchKey")

    assert MinioStorage(client).read("artifacts", "a.json") is None


def test_read_propagates_other_errors():
    client = MagicMock()
    client.get_object.side_effect = s3_error("AccessDenied")

    with pytest.raises(S3Error):
        MinioStorage(client).read("artifacts", "a.json")


def test_from_settings_uses_configured_credentials(settings, monkeypatch):
    minio = MagicMock()
    monkeypatch.setattr("processing_service.storage.Minio", minio)
    configured = settings.model_copy(
        update={"minio_endpoint": "172.17.0.1:19000", "minio_secret_key": SecretStr("segredo")}
    )

    MinioStorage.from_settings(configured)

    minio.assert_called_once_with(
        "172.17.0.1:19000", access_key="video_insight", secret_key="segredo", secure=False
    )


@pytest.mark.integration
@requires_docker
def test_round_trip_against_real_minio(tmp_path):
    from testcontainers.community.minio import MinioContainer

    with MinioContainer(image=MINIO_IMAGE) as container:
        storage = MinioStorage(container.get_client())

        storage.upload("artifacts", "jobs/1/transcript.json", b'{"ok": true}', "application/json")
        storage.download("artifacts", "jobs/1/transcript.json", tmp_path / "copy.json")

        assert (tmp_path / "copy.json").read_bytes() == b'{"ok": true}'
        assert storage.read("artifacts", "jobs/1/transcript.json") == b'{"ok": true}'
        assert storage.read("artifacts", "jobs/1/missing.json") is None
        with pytest.raises(ProcessingError) as raised:
            storage.download("artifacts", "jobs/1/missing.mp4", tmp_path / "missing.mp4")
        assert raised.value.code == "video_not_found"
