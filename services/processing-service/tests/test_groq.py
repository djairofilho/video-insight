import httpx
import pytest
from pydantic import SecretStr

from processing_service.domain import ConfigurationError, ProcessingError
from processing_service.transcription.factory import create_transcriber
from processing_service.transcription.groq import GroqTranscriber

GROQ_BODY = {
    "text": "Olá, pessoal. Hoje falamos de fluidos.",
    "language": "Portuguese",
    "segments": [
        {"id": 0, "start": 0.0, "end": 4.2, "text": " Olá, pessoal."},
        {"id": 1, "start": 4.2, "end": 9.9, "text": "   "},
        {"id": 2, "start": 9.5, "end": 12.4, "text": " Hoje falamos de fluidos."},
    ],
}


def responder(*responses):
    queue = list(responses)
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        response = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(response, Exception):
            raise response
        return response

    return handle, requests


def build(handler, *, max_attempts=3) -> tuple[GroqTranscriber, list[float]]:
    sleeps: list[float] = []
    client = httpx.Client(
        base_url="https://groq.test/openai/v1", transport=httpx.MockTransport(handler)
    )
    transcriber = GroqTranscriber(
        client,
        model="whisper-large-v3-turbo",
        language="pt",
        max_attempts=max_attempts,
        max_retry_wait_seconds=5,
        sleep=sleeps.append,
    )
    return transcriber, sleeps


@pytest.fixture
def audio(tmp_path):
    path = tmp_path / "audio.flac"
    path.write_bytes(b"fLaC")
    return path


def test_sends_verbose_json_request_and_parses_segments(audio):
    handler, requests = responder(httpx.Response(200, json=GROQ_BODY))
    transcriber, _ = build(handler)

    transcript = transcriber.transcribe(audio, duration_seconds=12.0)

    request = requests[0]
    assert request.url.path == "/openai/v1/audio/transcriptions"
    for field in (b"whisper-large-v3-turbo", b"verbose_json", b"segment", b'name="language"'):
        assert field in request.content
    assert [segment.text for segment in transcript.segments] == [
        "Olá, pessoal.",
        "Hoje falamos de fluidos.",
    ]
    assert transcript.segments[-1].end_seconds == 12.0
    assert transcript.language == "pt"
    assert transcriber.model.provider == "groq"
    assert transcriber.model.model == "whisper-large-v3-turbo"


def test_silent_audio_produces_empty_transcript(audio):
    handler, _ = responder(httpx.Response(200, json={"text": "", "segments": []}))
    transcriber, _ = build(handler)

    assert transcriber.transcribe(audio, duration_seconds=5.0).segments == ()


def test_rate_limit_waits_for_retry_after_up_to_the_cap(audio):
    handler, requests = responder(
        httpx.Response(429, headers={"retry-after": "7"}, text="slow down"),
        httpx.Response(200, json=GROQ_BODY),
    )
    transcriber, sleeps = build(handler)

    transcriber.transcribe(audio, duration_seconds=12.0)

    assert len(requests) == 2
    assert sleeps == [5]


def test_server_errors_back_off_exponentially(audio):
    handler, _ = responder(
        httpx.Response(503), httpx.Response(502), httpx.Response(200, json=GROQ_BODY)
    )
    transcriber, sleeps = build(handler)

    transcriber.transcribe(audio, duration_seconds=12.0)

    assert sleeps == [2.0, 4.0]


def test_gives_up_after_max_attempts(audio):
    handler, requests = responder(httpx.Response(500, text="erro interno"))
    transcriber, sleeps = build(handler, max_attempts=2)

    with pytest.raises(ProcessingError) as raised:
        transcriber.transcribe(audio, duration_seconds=12.0)

    assert (raised.value.code, raised.value.retryable) == ("transcription_unavailable", True)
    assert "500" in raised.value.message
    assert len(requests) == 2
    assert len(sleeps) == 1


def test_network_failures_are_retryable(audio):
    handler, _ = responder(httpx.ConnectError("sem rota"))
    transcriber, sleeps = build(handler)

    with pytest.raises(ProcessingError) as raised:
        transcriber.transcribe(audio, duration_seconds=12.0)

    assert (raised.value.code, raised.value.retryable) == ("transcription_unavailable", True)
    assert sleeps == [2.0, 4.0]


def test_client_errors_are_not_retried(audio):
    handler, requests = responder(httpx.Response(400, text="arquivo inválido"))
    transcriber, sleeps = build(handler)

    with pytest.raises(ProcessingError) as raised:
        transcriber.transcribe(audio, duration_seconds=12.0)

    assert (raised.value.code, raised.value.retryable) == ("transcription_rejected", False)
    assert len(requests) == 1
    assert sleeps == []


def test_create_authenticates_with_the_api_key(audio):
    handler, requests = responder(httpx.Response(200, json=GROQ_BODY))
    transcriber = GroqTranscriber.create(
        api_key="chave-secreta",
        base_url="https://groq.test/openai/v1",
        timeout_seconds=10,
        model="whisper-large-v3-turbo",
        language="pt",
        max_attempts=1,
        max_retry_wait_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    transcriber.transcribe(audio, duration_seconds=12.0)

    assert requests[0].headers["authorization"] == "Bearer chave-secreta"


def test_factory_builds_groq_from_settings(settings):
    configured = settings.model_copy(update={"groq_api_key": SecretStr("chave")})

    transcriber = create_transcriber(configured)

    assert isinstance(transcriber, GroqTranscriber)
    assert transcriber.model.model == configured.groq_model


def test_factory_requires_api_key(settings):
    with pytest.raises(ConfigurationError, match="GROQ_API_KEY"):
        create_transcriber(settings.model_copy(update={"groq_api_key": SecretStr("")}))


def test_factory_rejects_unknown_provider(settings):
    with pytest.raises(ConfigurationError, match="desconhecido"):
        create_transcriber(settings.model_copy(update={"transcription_provider": "whisper-local"}))
