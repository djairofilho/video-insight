import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from processing_service import app as app_module
from processing_service.config import Settings
from processing_service.domain import ConfigurationError
from processing_service.messaging.rabbitmq import RabbitMQWorker
from processing_service.pipeline import ProcessingPipeline
from processing_service.worker import build_pipeline, build_worker


class FakeWorker:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.connected = True

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


def use_settings(monkeypatch, **values) -> None:
    monkeypatch.setattr(app_module, "get_settings", lambda: Settings(**values))


def test_lifespan_starts_and_stops_the_worker(monkeypatch):
    worker = FakeWorker()
    use_settings(monkeypatch, consumer_enabled=True)
    monkeypatch.setattr(app_module, "build_worker", lambda settings: worker)

    with TestClient(app_module.app) as client:
        assert client.get("/health").json()["consumer"] == "connected"
        worker.connected = False
        assert client.get("/health").json()["consumer"] == "connecting"
        assert worker.started

    assert worker.stopped


def test_missing_credentials_keep_the_http_api_up(monkeypatch):
    def fail(settings):
        raise ConfigurationError("GROQ_API_KEY não foi definido")

    use_settings(monkeypatch, consumer_enabled=True)
    monkeypatch.setattr(app_module, "build_worker", fail)

    with TestClient(app_module.app) as client:
        assert client.get("/health").json()["consumer"] == "disabled"


def test_consumer_can_be_disabled_by_configuration(monkeypatch):
    def unexpected(settings):
        raise AssertionError("não deveria montar o worker")

    use_settings(monkeypatch, consumer_enabled=False)
    monkeypatch.setattr(app_module, "build_worker", unexpected)

    with TestClient(app_module.app) as client:
        assert client.get("/health").json()["consumer"] == "disabled"


CREDENTIALS = {
    "rabbitmq_password": SecretStr("rabbit"),
    "minio_secret_key": SecretStr("minio"),
    "groq_api_key": SecretStr("groq"),
    "gemini_api_key": SecretStr("gemini"),
}


def test_composition_root_wires_the_real_components():
    settings = Settings(**CREDENTIALS)

    assert isinstance(build_pipeline(settings), ProcessingPipeline)
    assert isinstance(build_worker(settings), RabbitMQWorker)


@pytest.mark.parametrize(
    ("missing", "variable"),
    [
        ("rabbitmq_password", "RABBITMQ_PASSWORD"),
        ("minio_secret_key", "MINIO_SECRET_KEY"),
        ("groq_api_key", "GROQ_API_KEY"),
        ("gemini_api_key", "GEMINI_API_KEY"),
    ],
)
def test_missing_credentials_are_configuration_errors(missing, variable):
    settings = Settings(**{**CREDENTIALS, missing: SecretStr("")})

    with pytest.raises(ConfigurationError, match=variable):
        build_worker(settings)
