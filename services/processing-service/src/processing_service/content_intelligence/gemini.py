import logging
import time
from collections.abc import Callable, Sequence

import httpx
from google import genai
from google.genai import errors, types

from processing_service.content_intelligence.agent import Tool, ToolCall, ToolResult
from processing_service.domain import ProcessingError

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {408, 429}


class GeminiChatModel:
    provider = "google"

    def __init__(
        self,
        client: genai.Client,
        *,
        model: str,
        fallback_model: str | None,
        thinking_level: str,
        call_attempts: int,
        max_backoff_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self.model = model
        self._fallback_model = fallback_model
        self._thinking_level = thinking_level
        self._call_attempts = call_attempts
        self._max_backoff = max_backoff_seconds
        self._sleep = sleep

    @classmethod
    def create(
        cls,
        *,
        api_key: str,
        model: str,
        fallback_model: str | None,
        thinking_level: str,
        timeout_seconds: float,
        call_attempts: int,
        max_backoff_seconds: float,
    ) -> "GeminiChatModel":
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        return cls(
            client,
            model=model,
            fallback_model=fallback_model,
            thinking_level=thinking_level,
            call_attempts=call_attempts,
            max_backoff_seconds=max_backoff_seconds,
        )

    def open_session(self, system_prompt: str, tools: Sequence[Tool]) -> "GeminiSession":
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=tool.name,
                            description=tool.description,
                            parameters_json_schema=_parameters(tool),
                        )
                        for tool in tools
                    ]
                )
            ],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="ANY")
            ),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=types.ThinkingConfig(thinking_level=self._thinking_level),
        )
        return GeminiSession(self, config)

    def generate(
        self, contents: list[types.Content], config: types.GenerateContentConfig
    ) -> tuple[types.GenerateContentResponse, str]:
        models = self._rotation()
        for attempt, model in enumerate(models, start=1):
            try:
                response = self._client.models.generate_content(
                    model=model, contents=contents, config=config
                )
            except errors.APIError as error:
                message = f"Gemini ({model}) respondeu {error.code}: {error.message}"
                if error.code not in _RETRYABLE_STATUS and error.code < 500:
                    raise ProcessingError("llm_rejected", message, retryable=False) from error
                failure = ProcessingError("llm_unavailable", message, retryable=True)
            except httpx.TransportError as error:
                failure = ProcessingError(
                    "llm_unavailable", f"Falha de rede com o Gemini: {error}", retryable=True
                )
            else:
                _log_usage(model, response)
                return response, model
            if attempt == len(models):
                raise failure
            logger.warning("%s; nova tentativa com %s", failure.message, models[attempt])
            self._sleep(min(2.0**attempt, self._max_backoff))
        raise AssertionError("unreachable")

    def _rotation(self) -> list[str]:
        if not self._fallback_model:
            return [self.model] * self._call_attempts
        return [
            self.model if attempt % 2 == 0 else self._fallback_model
            for attempt in range(self._call_attempts)
        ]


class GeminiSession:
    def __init__(self, model: GeminiChatModel, config: types.GenerateContentConfig) -> None:
        self._model = model
        self._config = config
        self._contents: list[types.Content] = []
        self.served: list[tuple[str, str]] = []

    def send(self, *, text: str | None = None, results: Sequence[ToolResult] = ()) -> list[ToolCall]:
        parts = [
            types.Part(
                function_response=types.FunctionResponse(
                    id=result.call.id, name=result.call.name, response=result.content
                )
            )
            for result in results
        ]
        if text:
            parts.append(types.Part.from_text(text=text))
        self._contents.append(types.Content(role="user", parts=parts))
        response, model = self._model.generate(self._contents, self._config)
        self.served.append((model, response.model_version or model))
        candidate = response.candidates[0] if response.candidates else None
        if candidate is None or candidate.content is None:
            reason = response.prompt_feedback or (candidate.finish_reason if candidate else None)
            raise ProcessingError(
                "llm_blocked", f"Gemini não retornou conteúdo ({reason})", retryable=False
            )
        self._contents.append(candidate.content)
        return [
            ToolCall(id=call.id, name=call.name or "", arguments=dict(call.args or {}))
            for call in response.function_calls or ()
        ]


def _parameters(tool: Tool) -> dict | None:
    schema = tool.arguments.model_json_schema()
    return schema if schema.get("properties") else None


def _log_usage(model: str, response: types.GenerateContentResponse) -> None:
    usage = response.usage_metadata
    if usage is not None:
        logger.info(
            "%s tokens: entrada=%s saída=%s raciocínio=%s",
            model,
            usage.prompt_token_count,
            usage.candidates_token_count,
            usage.thoughts_token_count,
        )
