import httpx
import pytest
from google.genai import errors, types
from pydantic import BaseModel, Field

from processing_service.content_intelligence.agent import Tool, ToolCall, ToolResult
from processing_service.content_intelligence.gemini import GeminiChatModel
from processing_service.domain import ProcessingError


class SubmitArgs(BaseModel):
    markdown: str = Field(min_length=1)


TOOL = Tool("submit_summary", "Entrega o resumo", SubmitArgs, lambda args: {"ok": True})


class FakeModels:
    def __init__(self, outcomes) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": list(contents), "config": config})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, *outcomes) -> None:
        self.models = FakeModels(outcomes)


def function_call(name="submit_summary", args=None, version="gemini-3.5-flash-lite-001"):
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                id="call-1", name=name, args=args or {"markdown": "texto"}
                            ),
                            thought_signature=b"assinatura",
                        )
                    ],
                )
            )
        ],
        model_version=version,
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=120, candidates_token_count=30, thoughts_token_count=10
        ),
    )


def build(
    *outcomes, attempts=3, fallback="gemini-3.1-flash-lite", max_backoff=16.0
) -> tuple[GeminiChatModel, FakeClient, list[float]]:
    client = FakeClient(*outcomes)
    sleeps: list[float] = []
    model = GeminiChatModel(
        client,
        model="gemini-3.5-flash-lite",
        fallback_model=fallback,
        thinking_level="medium",
        call_attempts=attempts,
        max_backoff_seconds=max_backoff,
        sleep=sleeps.append,
    )
    return model, client, sleeps


def api_error(kind, code: int, status: str):
    return kind(code, {"error": {"code": code, "message": "falhou", "status": status}})


def test_session_config_forces_tool_use_and_declares_tools():
    model, client, _ = build(function_call())

    model.open_session("instruções", [TOOL]).send(text="transcrição")

    config = client.models.calls[0]["config"]
    declaration = config.tools[0].function_declarations[0]
    assert config.system_instruction == "instruções"
    assert declaration.name == "submit_summary"
    assert declaration.description == "Entrega o resumo"
    assert declaration.parameters_json_schema["required"] == ["markdown"]
    assert config.tool_config.function_calling_config.mode == "ANY"
    assert config.automatic_function_calling.disable is True
    assert config.thinking_config.thinking_level == types.ThinkingLevel.MEDIUM
    assert config.temperature is None
    assert client.models.calls[0]["model"] == "gemini-3.5-flash-lite"


def test_keeps_model_turns_intact_and_answers_each_call_by_id():
    first = function_call()
    model, client, _ = build(first, function_call(args={"markdown": "novo"}))
    session = model.open_session("instruções", [TOOL])

    calls = session.send(text="transcrição")
    session.send(results=[ToolResult(call=calls[0], content={"error": "curto"})])

    assert calls == [ToolCall(id="call-1", name="submit_summary", arguments={"markdown": "texto"})]
    history = client.models.calls[1]["contents"]
    assert history[0].parts[0].text == "transcrição"
    assert history[1] is first.candidates[0].content
    assert history[1].parts[0].thought_signature == b"assinatura"
    response = history[2].parts[0].function_response
    assert (response.id, response.name, response.response) == (
        "call-1",
        "submit_summary",
        {"error": "curto"},
    )
    assert session.served == [
        ("gemini-3.5-flash-lite", "gemini-3.5-flash-lite-001"),
        ("gemini-3.5-flash-lite", "gemini-3.5-flash-lite-001"),
    ]


def test_text_only_answers_return_no_calls():
    reply = types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part(text="oi")]))]
    )
    model, _, _ = build(reply)
    session = model.open_session("instruções", [TOOL])

    assert session.send(text="transcrição") == []
    assert session.served == [("gemini-3.5-flash-lite", "gemini-3.5-flash-lite")]


@pytest.mark.parametrize(
    "error",
    [
        api_error(errors.ServerError, 503, "UNAVAILABLE"),
        api_error(errors.ClientError, 429, "RESOURCE_EXHAUSTED"),
        httpx.ConnectError("sem rota"),
    ],
    ids=["503", "429", "rede"],
)
def test_transient_failures_switch_to_the_fallback_model(error):
    model, client, sleeps = build(error, function_call(version="gemini-3.1-flash-lite-001"))
    session = model.open_session("instruções", [TOOL])

    calls = session.send(text="transcrição")

    assert calls[0].name == "submit_summary"
    assert sleeps == [2.0]
    assert [call["model"] for call in client.models.calls] == [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    ]
    assert session.served == [("gemini-3.1-flash-lite", "gemini-3.1-flash-lite-001")]


def test_rotation_alternates_models_and_caps_the_backoff():
    overloaded = [api_error(errors.ServerError, 503, "UNAVAILABLE") for _ in range(4)]
    model, client, sleeps = build(*overloaded, function_call(), attempts=5, max_backoff=5.0)

    model.open_session("instruções", [TOOL]).send(text="transcrição")

    assert [call["model"] for call in client.models.calls] == [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
    ]
    assert sleeps == [2.0, 4.0, 5.0, 5.0]


def test_without_fallback_every_attempt_uses_the_main_model():
    model, client, _ = build(
        api_error(errors.ServerError, 503, "UNAVAILABLE"), function_call(), fallback=None
    )

    model.open_session("instruções", [TOOL]).send(text="transcrição")

    assert {call["model"] for call in client.models.calls} == {"gemini-3.5-flash-lite"}


def test_gives_up_after_the_configured_attempts():
    model, _, sleeps = build(
        api_error(errors.ServerError, 500, "INTERNAL"),
        api_error(errors.ServerError, 500, "INTERNAL"),
        attempts=2,
    )

    with pytest.raises(ProcessingError) as raised:
        model.open_session("instruções", [TOOL]).send(text="transcrição")

    assert (raised.value.code, raised.value.retryable) == ("llm_unavailable", True)
    assert sleeps == [2.0]


def test_client_errors_are_not_retried():
    model, client, sleeps = build(api_error(errors.ClientError, 400, "INVALID_ARGUMENT"))

    with pytest.raises(ProcessingError) as raised:
        model.open_session("instruções", [TOOL]).send(text="transcrição")

    assert (raised.value.code, raised.value.retryable) == ("llm_rejected", False)
    assert "400" in raised.value.message
    assert sleeps == []
    assert len(client.models.calls) == 1


def test_blocked_responses_fail_without_retry():
    model, _, _ = build(types.GenerateContentResponse(candidates=[]))

    with pytest.raises(ProcessingError) as raised:
        model.open_session("instruções", [TOOL]).send(text="transcrição")

    assert (raised.value.code, raised.value.retryable) == ("llm_blocked", False)


def test_create_builds_a_configured_client():
    model = GeminiChatModel.create(
        api_key="chave",
        model="gemini-3.5-flash-lite",
        fallback_model="gemini-3.1-flash-lite",
        thinking_level="low",
        timeout_seconds=30,
        call_attempts=2,
        max_backoff_seconds=16,
    )

    assert model.model == "gemini-3.5-flash-lite"
    assert model.provider == "google"
