import socket
from functools import lru_cache
from typing import Literal
from urllib.parse import quote

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    worker_id: str = Field(default_factory=socket.gethostname)
    consumer_enabled: bool = True

    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "video_insight"
    rabbitmq_password: SecretStr = SecretStr("")
    rabbitmq_vhost: str = "/"
    rabbitmq_reconnect_seconds: float = 5.0
    event_publish_timeout_seconds: float = 30.0

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "video_insight"
    minio_secret_key: SecretStr = SecretStr("")
    minio_secure: bool = False
    videos_bucket: str = "videos"
    artifacts_bucket: str = "artifacts"

    max_video_duration_seconds: float = 600.0
    max_video_size_bytes: int = 104_857_600
    ffmpeg_timeout_seconds: float = 120.0

    transcription_provider: Literal["groq"] = "groq"
    transcription_language: str = "pt"
    groq_api_key: SecretStr = SecretStr("")
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "whisper-large-v3-turbo"
    groq_timeout_seconds: float = 120.0
    groq_max_attempts: int = Field(default=3, ge=1)
    groq_max_retry_wait_seconds: float = 20.0

    content_provider: Literal["gemini"] = "gemini"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_fallback_model: str = "gemini-3.1-flash-lite"
    gemini_thinking_level: Literal["minimal", "low", "medium", "high"] = "medium"
    gemini_timeout_seconds: float = 90.0
    gemini_call_attempts: int = Field(default=5, ge=1)
    gemini_max_backoff_seconds: float = 16.0

    agent_max_nudges: int = Field(default=2, ge=0)
    summary_agent_max_turns: int = Field(default=6, ge=2)
    summary_agent_max_tool_calls: int = Field(default=8, ge=2)
    summary_agent_wall_clock_seconds: float = 150.0
    chapter_agent_max_turns: int = Field(default=16, ge=3)
    chapter_agent_max_tool_calls: int = Field(default=24, ge=3)
    chapter_agent_wall_clock_seconds: float = 360.0

    log_level: str = "INFO"

    @property
    def rabbitmq_url(self) -> str:
        user = quote(self.rabbitmq_user, safe="")
        password = quote(self.rabbitmq_password.get_secret_value(), safe="")
        vhost = quote(self.rabbitmq_vhost, safe="")
        return f"amqp://{user}:{password}@{self.rabbitmq_host}:{self.rabbitmq_port}/{vhost}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
