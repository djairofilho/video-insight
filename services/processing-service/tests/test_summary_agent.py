import pytest

from processing_service.content_intelligence.agent import AgentLimits, AgentRunner
from processing_service.content_intelligence.summary_agent import (
    STYLE_GUIDES,
    AgentSummarizer,
    SummaryToolbox,
    validate_summary,
)
from processing_service.domain import Operation, ProcessingError, Transcript, TranscriptSegment
from support import ScriptedChatModel, call

LIMITS = AgentLimits(max_turns=6, max_tool_calls=8, max_nudges=2, wall_clock_seconds=60)

TRANSCRIPT = Transcript(
    language="pt",
    duration_seconds=20.0,
    segments=(
        TranscriptSegment(start_seconds=0.0, end_seconds=8.5, text="Hoje vamos falar de fluidos."),
        TranscriptSegment(start_seconds=8.5, end_seconds=20.0, text="A pressão mantém o equilíbrio."),
    ),
)

LESSON = (
    "Os fluidos incompressíveis preservam volume e a pressão atua para manter esse equilíbrio. "
    "A aula apresenta a ideia central e a relaciona com exemplos do cotidiano.\n\n"
    "### Conceitos centrais\n"
    "- **Incompressibilidade**: o volume local não muda enquanto o fluido escoa.\n"
    "- **Pressão**: ajusta o escoamento para que a divergência permaneça nula.\n"
    "- **Viscosidade**: difunde momento entre camadas vizinhas do fluido.\n"
)

MEETING = (
    "Reunião semanal da equipe para alinhar a entrega do projeto de software.\n\n"
    "**Decisões**\n"
    "- A entrega dois prioriza o serviço de processamento e os testes automatizados.\n"
    "- O gateway recebe as rotas novas depois que os contratos forem aprovados.\n\n"
    "**Pendências e responsáveis**\n"
    "- Marcus define a topologia do RabbitMQ até sexta-feira.\n"
)


def summarizer(*turns) -> tuple[AgentSummarizer, ScriptedChatModel]:
    chat = ScriptedChatModel(*turns)
    return AgentSummarizer(AgentRunner(chat, LIMITS)), chat


def test_classifies_then_submits_a_valid_summary():
    agent, chat = summarizer(
        [call("classify_content", content_kind="lecture", rationale="Explica conceitos de física")],
        [call("submit_summary", markdown="curto demais")],
        [call("submit_summary", markdown=LESSON)],
    )

    summary = agent.summarize(TRANSCRIPT)

    assert summary.content_kind == "lecture"
    assert summary.text == LESSON.strip()
    assert chat.results_for("classify_content") == [{"ok": True, "style_guide": STYLE_GUIDES["lecture"]}]
    first_attempt = chat.results_for("submit_summary")[0]["error"]
    assert first_attempt.startswith("Resumo inválido: tem 2 palavras")
    assert "[0.0s – 8.5s] Hoje vamos falar de fluidos." in chat.sent[0][0]


def test_submitting_before_classifying_is_rejected():
    toolbox = SummaryToolbox()

    result = toolbox.execute(call("submit_summary", markdown=MEETING))

    assert result == {"error": "Chame classify_content antes de submit_summary."}
    assert toolbox.next_step() == "chame classify_content."


def test_next_step_after_classification_asks_for_the_summary():
    toolbox = SummaryToolbox()
    toolbox.execute(call("classify_content", content_kind="meeting", rationale="Reunião"))

    assert toolbox.next_step() == "chame submit_summary com o resumo."


@pytest.mark.parametrize(
    ("markdown", "kind", "problem"),
    [
        ("```\ncódigo\n```\n" + MEETING, "meeting", "remova blocos de código"),
        ("# Título\n" + MEETING, "meeting", "não use título de nível 1 (#)"),
        (MEETING.replace("- ", ""), "meeting", "inclua ao menos uma lista"),
        (LESSON.replace("**", ""), "lecture", "destaque os termos-chave em **negrito**"),
        ("palavra " * 400 + "\n- item", "other", "tem 402 palavras"),
    ],
    ids=["codigo", "titulo", "sem-lista", "sem-negrito", "longo"],
)
def test_validation_rules(markdown, kind, problem):
    assert any(found.startswith(problem) for found in validate_summary(markdown, kind))


@pytest.mark.parametrize(
    ("opening", "found"),
    [
        ("Este vídeo explica a fotossíntese.", "Este vídeo"),
        ("Neste vídeo, vemos a fotossíntese.", "Neste vídeo"),
        ("Nesta aula, vemos a fotossíntese.", "Nesta aula"),
        ("O professor explica a fotossíntese.", "O professor explica"),
    ],
)
def test_meta_text_is_rejected(opening, found):
    problems = validate_summary(f"{opening}\n\n{LESSON}", "lecture")

    assert problems == [
        f"remova o meta-texto '{found}': não fale do vídeo, apresente o conteúdo direto"
    ]


def test_meeting_without_bold_is_accepted():
    assert validate_summary(MEETING.replace("**", ""), "meeting") == []


def test_empty_transcript_is_not_summarized():
    agent, chat = summarizer()
    empty = Transcript(language="pt", duration_seconds=5.0, segments=())

    with pytest.raises(ProcessingError) as raised:
        agent.summarize(empty)

    assert (raised.value.code, raised.value.retryable) == ("no_speech", False)
    assert chat.sent == []


def test_agent_that_never_submits_fails_retryably():
    agent, _ = summarizer(
        [call("classify_content", content_kind="lecture", rationale="Aula")], [], [], []
    )

    with pytest.raises(ProcessingError) as raised:
        agent.summarize(TRANSCRIPT)

    assert (raised.value.code, raised.value.retryable) == ("summary_incomplete", True)


def test_model_reference_describes_the_summary():
    agent, _ = summarizer()

    assert agent.model.purpose == Operation.SUMMARY
    assert agent.model.model == "scripted-model"
