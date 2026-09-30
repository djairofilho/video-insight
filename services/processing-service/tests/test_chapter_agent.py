import pytest

from processing_service.content_intelligence.agent import AgentLimits, AgentRunner
from processing_service.content_intelligence.chapter_agent import (
    AgentChapterWriter,
    ChapterToolbox,
    chapter_bounds,
)
from processing_service.content_intelligence.models import ChapterList
from processing_service.domain import Operation, ProcessingError, Transcript, TranscriptSegment
from support import ScriptedChatModel, call
from test_blocks import CALLOUT, CYCLE, FLOW, PARAGRAPH

LIMITS = AgentLimits(max_turns=10, max_tool_calls=20, max_nudges=2, wall_clock_seconds=60)

TRANSCRIPT = Transcript(
    language="pt",
    duration_seconds=150.0,
    segments=(
        TranscriptSegment(start_seconds=0.0, end_seconds=50.0, text="Incompressibilidade preserva volume."),
        TranscriptSegment(start_seconds=50.0, end_seconds=100.0, text="A pressão mantém a divergência nula."),
        TranscriptSegment(start_seconds=100.0, end_seconds=150.0, text="A viscosidade difunde momento."),
    ),
)


def outline_entry(number, title, start, end):
    return {
        "number": number,
        "title": title,
        "start_seconds": start,
        "end_seconds": end,
        "focus": f"O que o trecho {number} ensina.",
    }


OUTLINE = [
    outline_entry(1, "Incompressibilidade", 0.0, 61.0),
    outline_entry(2, "Pressão e viscosidade", 62.0, 149.0),
]
FIRST_BLOCKS = [PARAGRAPH, FLOW, PARAGRAPH, CALLOUT]
SECOND_BLOCKS = [PARAGRAPH, PARAGRAPH]


def writer(*turns) -> tuple[AgentChapterWriter, ScriptedChatModel]:
    chat = ScriptedChatModel(*turns)
    return AgentChapterWriter(AgentRunner(chat, LIMITS)), chat


def outlined_toolbox() -> ChapterToolbox:
    toolbox = ChapterToolbox(150.0)
    assert toolbox.execute(call("publish_outline", chapters=OUTLINE))["ok"]
    return toolbox


def test_writes_contiguous_chapters_following_the_outline():
    agent, chat = writer(
        [call("publish_outline", chapters=OUTLINE)],
        [call("emit_chapter", number=1, blocks=FIRST_BLOCKS)],
        [call("emit_chapter", number=2, blocks=SECOND_BLOCKS)],
        [call("finish")],
    )

    chapters = agent.write_chapters(TRANSCRIPT)

    assert [(c.title, c.start_seconds, c.end_seconds) for c in chapters] == [
        ("Incompressibilidade", 0.0, 61.0),
        ("Pressão e viscosidade", 61.0, 150.0),
    ]
    assert [block.type for block in chapters[0].blocks] == ["paragraph", "flow", "paragraph", "callout"]
    assert ChapterList.model_validate_json(ChapterList(chapters=chapters).model_dump_json())
    assert "Duração do vídeo: 150.0s. Use entre 2 e 3 capítulos." in chat.sent[0][0]
    assert "[50.0s – 100.0s] A pressão mantém a divergência nula." in chat.sent[0][0]
    assert chat.results_for("publish_outline")[0]["next"] == (
        "chame emit_chapter 1 (Incompressibilidade, 0s–61s)."
    )


@pytest.mark.parametrize(
    ("chapters", "problem"),
    [
        ([outline_entry(1, "Tudo", 0.0, 150.0)], "use entre 2 e 3 capítulos (recebeu 1)"),
        (
            [outline_entry(1, "A", 0.0, 75.0), outline_entry(3, "B", 75.0, 150.0)],
            "numere os capítulos de 1 a N",
        ),
        (
            [outline_entry(1, "A", 10.0, 75.0), outline_entry(2, "B", 75.0, 150.0)],
            "o primeiro capítulo deve começar em 0s",
        ),
        (
            [outline_entry(1, "A", 0.0, 75.0), outline_entry(2, "B", 75.0, 120.0)],
            "o último capítulo deve terminar em 150.0s",
        ),
        (
            [outline_entry(1, "A", 0.0, 50.0), outline_entry(2, "B", 60.0, 150.0)],
            "o capítulo 2 deve começar onde o 1 termina (50.0s)",
        ),
        (
            [outline_entry(1, "A", 0.0, 10.0), outline_entry(2, "B", 10.0, 150.0)],
            "o capítulo 1 tem menos de 20s",
        ),
        (
            [outline_entry(1, "A", 0.0, 80.0), outline_entry(2, "B", 80.0, 70.0)],
            "o capítulo 2 termina antes de começar",
        ),
    ],
    ids=["poucos", "numeracao", "inicio", "fim", "buraco", "curto", "invertido"],
)
def test_outline_validation(chapters, problem):
    toolbox = ChapterToolbox(150.0)

    result = toolbox.execute(call("publish_outline", chapters=chapters))

    assert problem in result["error"]
    assert toolbox.outline == []


def test_outline_is_published_only_once():
    toolbox = outlined_toolbox()

    result = toolbox.execute(call("publish_outline", chapters=OUTLINE))

    assert result == {"error": "O sumário já foi publicado; siga com emit_chapter."}


def test_chapters_are_emitted_in_order_after_the_outline():
    toolbox = ChapterToolbox(150.0)
    assert toolbox.next_step() == "chame publish_outline com todos os capítulos."
    assert "publish_outline antes" in toolbox.execute(call("emit_chapter", number=1, blocks=SECOND_BLOCKS))["error"]

    toolbox.execute(call("publish_outline", chapters=OUTLINE))
    out_of_order = toolbox.execute(call("emit_chapter", number=2, blocks=SECOND_BLOCKS))

    assert out_of_order == {"error": "O próximo capítulo esperado é o 1."}


@pytest.mark.parametrize(
    ("blocks", "problem"),
    [
        ([{"kind": "paragraph"}, PARAGRAPH], "blocks[1] (paragraph): text é obrigatório"),
        ([FLOW, PARAGRAPH], "o capítulo deve começar com um paragraph"),
        ([PARAGRAPH], "use entre 2 e 8 blocos"),
    ],
    ids=["bloco-invalido", "ritmo", "curto"],
)
def test_emit_reports_problems(blocks, problem):
    toolbox = outlined_toolbox()

    result = toolbox.execute(call("emit_chapter", number=1, blocks=blocks))

    assert problem in result["error"]
    assert result["attempt"] == 1


def test_repeated_failures_accept_the_valid_blocks():
    toolbox = outlined_toolbox()
    broken = [PARAGRAPH, {**CYCLE, "stages": ["só", "duas"]}]

    results = [toolbox.execute(call("emit_chapter", number=1, blocks=broken)) for _ in range(3)]

    assert [result.get("attempt") for result in results[:2]] == [1, 2]
    assert results[2]["note"] == "Aceito sem 1 bloco(s) inválido(s) após tentativas repetidas."
    assert [block.type for block in toolbox.emitted[1]] == ["paragraph"]


def test_repeated_failures_without_any_paragraph_keep_failing():
    toolbox = outlined_toolbox()
    broken = [{"kind": "paragraph"}, CYCLE]

    results = [toolbox.execute(call("emit_chapter", number=1, blocks=broken)) for _ in range(4)]

    assert all("error" in result for result in results)
    assert 1 not in toolbox.emitted


def test_finish_requires_every_chapter():
    toolbox = ChapterToolbox(150.0)
    assert "publish_outline" in toolbox.execute(call("finish"))["error"]

    toolbox.execute(call("publish_outline", chapters=OUTLINE))
    toolbox.execute(call("emit_chapter", number=1, blocks=SECOND_BLOCKS))

    assert toolbox.execute(call("finish")) == {"error": "Capítulos ainda não emitidos: [2]."}
    toolbox.execute(call("emit_chapter", number=2, blocks=SECOND_BLOCKS))
    assert toolbox.next_step() == "chame finish."
    assert toolbox.execute(call("emit_chapter", number=3, blocks=SECOND_BLOCKS)) == {
        "error": "Todos os capítulos já foram emitidos; chame finish."
    }
    assert toolbox.execute(call("finish")) == {"ok": True}
    assert toolbox.finished


def test_partial_chapters_are_kept_when_the_agent_stops_early():
    agent, _ = writer(
        [call("publish_outline", chapters=OUTLINE)],
        [call("emit_chapter", number=1, blocks=SECOND_BLOCKS)],
        [],
        [],
        [],
    )

    chapters = agent.write_chapters(TRANSCRIPT)

    assert [chapter.title for chapter in chapters] == ["Incompressibilidade"]


def test_no_chapters_fails_retryably():
    agent, _ = writer([], [], [])

    with pytest.raises(ProcessingError) as raised:
        agent.write_chapters(TRANSCRIPT)

    assert (raised.value.code, raised.value.retryable) == ("chapters_incomplete", True)


def test_empty_transcript_is_not_sent_to_the_model():
    agent, chat = writer()

    with pytest.raises(ProcessingError) as raised:
        agent.write_chapters(Transcript(language="pt", duration_seconds=5.0, segments=()))

    assert (raised.value.code, raised.value.retryable) == ("no_speech", False)
    assert chat.sent == []


@pytest.mark.parametrize(
    ("duration", "bounds"),
    [(30.0, (1, 1)), (95.0, (1, 2)), (150.0, (2, 3)), (600.0, (2, 8)), (900.0, (2, 8))],
)
def test_chapter_bounds_scale_with_duration(duration, bounds):
    assert chapter_bounds(duration) == bounds


def test_model_reference_describes_the_chapters():
    agent, _ = writer()

    assert agent.model.purpose == Operation.CHAPTERS
