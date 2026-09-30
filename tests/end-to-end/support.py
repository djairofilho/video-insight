"""Chamadas aos serviços usadas pelos testes ponta a ponta."""

import struct
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx

FAKE_MEDIA = b"nao e um mp4 de verdade" * 64
ALL_OPERATIONS = ["transcription", "summary", "chapters"]
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


@dataclass
class Api:
    client: httpx.Client
    video_url: str
    job_url: str

    def create_video(self, size_bytes: int, file_name: str = "e2e.mp4",
                     content_type: str = "video/mp4") -> httpx.Response:
        return self.client.post(f"{self.video_url}/api/v1/videos", json={
            "file_name": file_name, "content_type": content_type, "size_bytes": size_bytes})

    def get_video(self, video_id: str) -> httpx.Response:
        return self.client.get(f"{self.video_url}/api/v1/videos/{video_id}")

    def list_videos(self, **params) -> httpx.Response:
        return self.client.get(f"{self.video_url}/api/v1/videos", params=params)

    def upload_url(self, video_id: str) -> httpx.Response:
        return self.client.post(f"{self.video_url}/api/v1/videos/{video_id}/upload-url")

    def complete_upload(self, video_id: str, duration_seconds: float) -> httpx.Response:
        return self.client.post(f"{self.video_url}/api/v1/videos/{video_id}/upload-complete",
                                json={"duration_seconds": duration_seconds})

    def playback_url(self, video_id: str) -> httpx.Response:
        return self.client.post(f"{self.video_url}/api/v1/videos/{video_id}/playback-url")

    def delete_video(self, video_id: str) -> httpx.Response:
        return self.client.delete(f"{self.video_url}/api/v1/videos/{video_id}")

    def put_file(self, signed_url: dict, content: bytes) -> httpx.Response:
        """Envia o arquivo direto ao MinIO, como o navegador faria."""
        return self.client.put(signed_url["url"], content=content, headers=signed_url.get("headers") or {})

    def upload(self, content: bytes, duration_seconds: float) -> str:
        """Cadastra, envia e confirma um vídeo; devolve o id do vídeo pronto."""
        video_id = self.create_video(len(content)).raise_for_status().json()["id"]
        signed = self.upload_url(video_id).raise_for_status().json()
        self.put_file(signed, content).raise_for_status()
        video = self.complete_upload(video_id, duration_seconds).raise_for_status().json()
        assert video["upload_status"] == "ready"
        return video_id

    def create_job(self, video_id: str, operations=None, idempotency_key: str | None = None) -> httpx.Response:
        return self.client.post(
            f"{self.job_url}/api/v1/videos/{video_id}/jobs",
            json={"operations": operations or ALL_OPERATIONS},
            headers={"Idempotency-Key": idempotency_key or f"e2e-{uuid.uuid4()}"})

    def get_job(self, job_id: str) -> httpx.Response:
        return self.client.get(f"{self.job_url}/api/v1/jobs/{job_id}")

    def cancel_job(self, job_id: str) -> httpx.Response:
        return self.client.post(f"{self.job_url}/api/v1/jobs/{job_id}/cancel")

    def retry_job(self, job_id: str) -> httpx.Response:
        return self.client.post(f"{self.job_url}/api/v1/jobs/{job_id}/retry")

    def job_result(self, job_id: str) -> httpx.Response:
        return self.client.get(f"{self.job_url}/api/v1/jobs/{job_id}/result")

    def export_transcript(self, job_id: str, fmt: str) -> httpx.Response:
        return self.client.get(f"{self.job_url}/api/v1/jobs/{job_id}/transcript", params={"format": fmt})

    def wait_for_job(self, job_id: str, timeout: float, statuses=TERMINAL_STATUSES) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            job = self.get_job(job_id).raise_for_status().json()
            if job["status"] in statuses:
                return job
            if time.monotonic() > deadline:
                raise AssertionError(f"Job {job_id} não terminou em {timeout:g}s: {job}")
            time.sleep(2)


def run_together(count: int, task) -> list:
    """Executa ``task(i)`` em ``count`` threads ao mesmo tempo e devolve os resultados em ordem."""
    with ThreadPoolExecutor(max_workers=count) as executor:
        return list(executor.map(task, range(count)))


def mp4_duration_seconds(content: bytes) -> float:
    """Lê a duração do átomo ``mvhd`` do MP4, sem depender do FFmpeg na máquina de teste."""
    index = content.find(b"mvhd")
    if index < 0:
        raise ValueError("MP4 sem átomo mvhd")
    version = content[index + 4]
    if version == 1:
        timescale, duration = struct.unpack(">IQ", content[index + 24:index + 36])
    else:
        timescale, duration = struct.unpack(">II", content[index + 16:index + 24])
    return round(duration / timescale, 3)
