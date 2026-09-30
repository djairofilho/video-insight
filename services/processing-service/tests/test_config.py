from pydantic import SecretStr

from processing_service.config import Settings, get_settings


def test_rabbitmq_url_escapes_credentials_and_vhost():
    settings = Settings(
        rabbitmq_user="user@insper",
        rabbitmq_password=SecretStr("p@ss/:w#"),
        rabbitmq_host="172.17.0.1",
        rabbitmq_port=15672,
        rabbitmq_vhost="/",
    )

    assert settings.rabbitmq_url == "amqp://user%40insper:p%40ss%2F%3Aw%23@172.17.0.1:15672/%2F"


def test_reads_environment_variables(monkeypatch):
    monkeypatch.setenv("RABBITMQ_HOST", "rabbitmq")
    monkeypatch.setenv("MINIO_SECRET_KEY", "segredo")
    monkeypatch.setenv("CONSUMER_ENABLED", "false")

    settings = Settings()

    assert settings.rabbitmq_host == "rabbitmq"
    assert settings.minio_secret_key.get_secret_value() == "segredo"
    assert settings.consumer_enabled is False


def test_secrets_are_not_exposed_in_repr():
    settings = Settings(rabbitmq_password=SecretStr("segredo"), groq_api_key=SecretStr("chave"))

    assert "segredo" not in repr(settings)
    assert "chave" not in repr(settings)


def test_get_settings_returns_a_single_instance():
    get_settings.cache_clear()

    assert get_settings() is get_settings()

    get_settings.cache_clear()
