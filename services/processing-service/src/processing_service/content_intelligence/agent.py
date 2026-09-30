import json
import logging
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from processing_service.domain import ModelReference, Operation

logger = logging.getLogger(__name__)

_MAX_REPORTED_ERRORS = 6


@dataclass(frozen=True)
class ToolCall:
    id: str | None
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    call: ToolCall
    content: dict[str, Any]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    arguments: type[BaseModel]
    handler: Callable[[Any], dict[str, Any]]


class ChatSession(Protocol):
    served: list[tuple[str, str]]

    def send(
        self, *, text: str | None = None, results: Sequence[ToolResult] = ()
    ) -> list[ToolCall]: ...


class ChatModel(Protocol):
    provider: str
    model: str

    def open_session(self, system_prompt: str, tools: Sequence[Tool]) -> ChatSession: ...


@dataclass(frozen=True)
class AgentLimits:
    max_turns: int
    max_tool_calls: int
    max_nudges: int
    wall_clock_seconds: float


@dataclass
class AgentStats:
    turns: int = 0
    tool_calls: int = 0
    nudges: int = 0
    finished: bool = False
    served: tuple[tuple[str, str], ...] = ()


class Toolbox:
    finish_tool: str

    def __init__(self, tools: Sequence[Tool]) -> None:
        self.tools = tuple(tools)
        self._by_name = {tool.name: tool for tool in tools}
        self.finished = False

    def next_step(self) -> str:
        raise NotImplementedError

    def execute(self, call: ToolCall) -> dict[str, Any]:
        tool = self._by_name.get(call.name)
        if tool is None:
            return {"error": f"Ferramenta desconhecida '{call.name}'."}
        try:
            arguments = tool.arguments.model_validate(call.arguments)
        except ValidationError as error:
            problems = [
                f"{'.'.join(str(part) for part in issue['loc']) or 'argumentos'}: {issue['msg']}"
                for issue in error.errors()[:_MAX_REPORTED_ERRORS]
            ]
            return {"error": f"Argumentos inválidos para {call.name}: " + "; ".join(problems)}
        try:
            return tool.handler(arguments)
        except Exception as error:
            logger.exception("Ferramenta %s falhou", call.name)
            return {"error": f"{call.name} falhou internamente ({type(error).__name__}). Ajuste e continue."}


class AgentRunner:
    def __init__(
        self,
        model: ChatModel,
        limits: AgentLimits,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._model = model
        self._limits = limits
        self._clock = clock

    @property
    def chat_model(self) -> ChatModel:
        return self._model

    def model_reference(
        self, purpose: Operation, served: Sequence[tuple[str, str]] = ()
    ) -> ModelReference:
        models = _unique(model for model, _ in served) or [self._model.model]
        versions = _unique(version for _, version in served) or models
        return ModelReference(
            purpose=purpose,
            provider=self._model.provider,
            model=" + ".join(models),
            version=" + ".join(versions),
        )

    def run(self, *, system_prompt: str, user_prompt: str, toolbox: Toolbox) -> AgentStats:
        limits = self._limits
        stats = AgentStats()
        started = self._clock()
        session = self._model.open_session(system_prompt, toolbox.tools)
        calls = session.send(text=user_prompt)
        stats.turns = 1
        while True:
            if not calls:
                if toolbox.finished:
                    break
                stats.nudges += 1
                if stats.nudges > limits.max_nudges or stats.turns >= limits.max_turns:
                    break
                calls = session.send(text=_nudge(toolbox))
                stats.turns += 1
                continue
            over_time = self._clock() - started > limits.wall_clock_seconds
            results = []
            for call in calls:
                stats.tool_calls += 1
                exhausted = over_time or stats.tool_calls > limits.max_tool_calls
                if exhausted and call.name != toolbox.finish_tool:
                    content = {"error": f"Orçamento esgotado. Chame {toolbox.finish_tool} agora."}
                else:
                    content = toolbox.execute(call)
                results.append(ToolResult(call=call, content=content))
            if toolbox.finished or stats.turns >= limits.max_turns:
                break
            calls = session.send(results=results)
            stats.turns += 1
        stats.finished = toolbox.finished
        stats.served = tuple(session.served)
        logger.info("Agente encerrado: %s", json.dumps(stats.__dict__))
        return stats


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _nudge(toolbox: Toolbox) -> str:
    return f"Não responda com texto. Use apenas ferramentas. Próximo passo: {toolbox.next_step()}"
