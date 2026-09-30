from pydantic import BaseModel, Field

from processing_service.content_intelligence.agent import (
    AgentLimits,
    AgentRunner,
    Tool,
    ToolCall,
    Toolbox,
)
from processing_service.domain import Operation
from support import ScriptedChatModel, call

LIMITS = AgentLimits(max_turns=6, max_tool_calls=5, max_nudges=2, wall_clock_seconds=60)


class NoteArgs(BaseModel):
    text: str = Field(min_length=1, max_length=20)


class FinishArgs(BaseModel):
    pass


class NotesToolbox(Toolbox):
    finish_tool = "finish"

    def __init__(self) -> None:
        super().__init__(
            [
                Tool("note", "Anota um texto", NoteArgs, self._note),
                Tool("finish", "Encerra", FinishArgs, self._finish),
                Tool("explode", "Sempre falha", FinishArgs, self._explode),
            ]
        )
        self.notes: list[str] = []

    def next_step(self) -> str:
        return "chame finish."

    def _note(self, args: NoteArgs) -> dict:
        self.notes.append(args.text)
        return {"ok": True}

    def _finish(self, args: FinishArgs) -> dict:
        self.finished = True
        return {"ok": True}

    def _explode(self, args: FinishArgs) -> dict:
        raise RuntimeError("quebrou")


def run(chat: ScriptedChatModel, limits: AgentLimits = LIMITS, clock=None):
    toolbox = NotesToolbox()
    runner = AgentRunner(chat, limits, **({"clock": clock} if clock else {}))
    stats = runner.run(system_prompt="sistema", user_prompt="usuário", toolbox=toolbox)
    return toolbox, stats


def test_toolbox_reports_unknown_tools_invalid_arguments_and_crashes():
    toolbox = NotesToolbox()

    assert "desconhecida" in toolbox.execute(ToolCall("1", "voar", {}))["error"]
    invalid = toolbox.execute(ToolCall("2", "note", {"text": "x" * 30}))["error"]
    assert invalid.startswith("Argumentos inválidos para note: text:")
    missing = toolbox.execute(ToolCall("3", "note", {}))["error"]
    assert "text" in missing
    assert "falhou internamente (RuntimeError)" in toolbox.execute(ToolCall("4", "explode", {}))["error"]
    assert toolbox.execute(ToolCall("5", "note", {"text": "ok"})) == {"ok": True}


def test_runs_tools_until_finish_without_extra_round_trip():
    chat = ScriptedChatModel([call("note", text="a"), call("note", text="b")], [call("finish")])

    toolbox, stats = run(chat)

    assert toolbox.notes == ["a", "b"]
    assert (stats.finished, stats.turns, stats.tool_calls, stats.nudges) == (True, 2, 3, 0)
    assert [text for text, _ in chat.sent] == ["usuário", None]
    assert chat.system_prompt == "sistema"
    assert [tool.name for tool in chat.tools] == ["note", "finish", "explode"]


def test_nudges_when_the_model_answers_without_tools():
    chat = ScriptedChatModel([], [call("finish")])

    toolbox, stats = run(chat)

    assert stats.finished
    assert stats.nudges == 1
    assert chat.sent[1][0] == "Não responda com texto. Use apenas ferramentas. Próximo passo: chame finish."


def test_gives_up_after_too_many_nudges():
    chat = ScriptedChatModel([], [], [], [call("finish")])

    toolbox, stats = run(chat)

    assert not stats.finished
    assert stats.nudges == 3
    assert stats.turns == 3


def test_stops_at_the_turn_limit():
    chat = ScriptedChatModel(*[[call("note", text=str(n))] for n in range(10)])

    toolbox, stats = run(chat, AgentLimits(max_turns=3, max_tool_calls=50, max_nudges=2, wall_clock_seconds=60))

    assert stats.turns == 3
    assert toolbox.notes == ["0", "1", "2"]
    assert not stats.finished


def test_exhausted_tool_budget_only_allows_finishing():
    chat = ScriptedChatModel(
        [call("note", text="a"), call("note", text="b")],
        [call("note", text="c")],
        [call("finish")],
    )

    toolbox, stats = run(chat, AgentLimits(max_turns=6, max_tool_calls=2, max_nudges=2, wall_clock_seconds=60))

    assert toolbox.notes == ["a", "b"]
    assert stats.finished
    assert chat.results_for("note")[-1] == {"error": "Orçamento esgotado. Chame finish agora."}


def test_wall_clock_limit_only_allows_finishing():
    ticks = iter([0.0, 61.0, 62.0])
    chat = ScriptedChatModel([call("note", text="a")], [call("finish")])

    toolbox, stats = run(chat, clock=lambda: next(ticks))

    assert toolbox.notes == []
    assert stats.finished


def test_run_reports_which_models_answered():
    chat = ScriptedChatModel([call("finish")])

    _, stats = run(chat)

    assert stats.served == (("scripted-model", "scripted-model-001"),)


def test_model_reference_lists_every_model_that_answered():
    chat = ScriptedChatModel()
    runner = AgentRunner(chat, LIMITS)

    default = runner.model_reference(Operation.SUMMARY)
    mixed = runner.model_reference(
        Operation.CHAPTERS, [("lead", "lead-001"), ("backup", "backup-002"), ("lead", "lead-001")]
    )

    assert (default.model, default.version, default.provider) == ("scripted-model", "scripted-model", "scripted")
    assert (mixed.purpose, mixed.model, mixed.version) == (
        Operation.CHAPTERS,
        "lead + backup",
        "lead-001 + backup-002",
    )
    assert runner.chat_model is chat
