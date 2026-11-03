"""Configuração dos testes ponta a ponta.

Os serviços precisam estar no ar (veja o README). Os endereços e o vídeo de
amostra vêm do ambiente ou das linhas ``E2E_*`` do ``.env`` da raiz.
"""

import os
from pathlib import Path

import httpx
import pytest

import support

ROOT = Path(__file__).resolve().parents[2]


def _env_file_values() -> dict[str, str]:
    """Lê só variáveis ``E2E_*``; ignora linhas que não sejam ``CHAVE=valor``."""
    path = ROOT / ".env"
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip().startswith("E2E_"):
            values[key.strip()] = value.strip().strip('"')
    return values


def _setting(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name) or _env_file_values().get(name) or default


@pytest.fixture(scope="session")
def api():
    gateway_url = _setting("E2E_GATEWAY_URL")
    gateway_url = gateway_url.rstrip("/") if gateway_url else None
    video_url = gateway_url or _setting("E2E_VIDEO_SERVICE_URL", "http://localhost:8081")
    job_url = gateway_url or _setting("E2E_JOB_SERVICE_URL", "http://localhost:8082")
    token = _setting("E2E_ACCESS_TOKEN")
    if not token:
        pytest.fail("Defina E2E_ACCESS_TOKEN com um access token válido para a API.")
    with httpx.Client(timeout=30, headers={"Authorization": f"Bearer {token}"}) as client:
        health_base = _setting("E2E_HEALTH_BASE_URL", gateway_url)
        health_urls = ([f"{health_base.rstrip('/')}/health/{name}" for name in ("video", "jobs", "processing")]
                       if gateway_url else [f"{url}/health" for url in (video_url, job_url)])
        for url in health_urls:
            try:
                response = client.get(url)
                response.raise_for_status()
                if response.json().get("status", "").lower() not in ("ok", "up", "healthy"):
                    pytest.fail(f"Dependência não está saudável em {url}.")
                if url.endswith("/health/processing") and response.json().get("consumer") != "connected":
                    pytest.fail("Processing Service não está conectado ao RabbitMQ.")
            except httpx.HTTPError as error:
                pytest.fail(f"Serviço fora do ar em {url}: {error}. Veja tests/end-to-end/README.md.")
        proxy = _setting("E2E_STORAGE_PROXY_BASE", f"{gateway_url}/storage" if gateway_url else None)
        yield support.Api(client, video_url, job_url, proxy)


@pytest.fixture(scope="session")
def other_api(api):
    token = _setting("E2E_OTHER_ACCESS_TOKEN")
    if not token:
        pytest.fail("Defina E2E_OTHER_ACCESS_TOKEN com um token de outra conta de teste.")
    with httpx.Client(timeout=30, headers={"Authorization": f"Bearer {token}"}) as client:
        yield support.Api(client, api.video_url, api.job_url, api.storage_proxy_base)


@pytest.fixture(scope="session")
def sample_video() -> tuple[bytes, float]:
    """Conteúdo e duração do MP4 com fala em português usado no fluxo completo."""
    path = _setting("E2E_SAMPLE_VIDEO")
    if not path or not Path(path).is_file():
        pytest.fail("Defina E2E_SAMPLE_VIDEO com o caminho de um MP4 curto com fala em português.")
    content = Path(path).read_bytes()
    return content, support.mp4_duration_seconds(content)


@pytest.fixture(scope="session")
def job_timeout() -> float:
    return float(_setting("E2E_JOB_TIMEOUT_SECONDS", "600"))
