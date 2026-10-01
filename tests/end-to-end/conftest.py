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
    video_url = _setting("E2E_VIDEO_SERVICE_URL", "http://localhost:8081")
    job_url = _setting("E2E_JOB_SERVICE_URL", "http://localhost:8082")
    with httpx.Client(timeout=30) as client:
        for url in (video_url, job_url):
            try:
                client.get(f"{url}/health").raise_for_status()
            except httpx.HTTPError as error:
                pytest.fail(f"Serviço fora do ar em {url}: {error}. Veja tests/end-to-end/README.md.")
        yield support.Api(client, video_url, job_url)


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
