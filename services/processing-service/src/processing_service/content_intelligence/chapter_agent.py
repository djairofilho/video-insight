import logging
import math
from typing import Any

from pydantic import BaseModel, Field

from processing_service.content_intelligence.agent import AgentRunner, Tool, Toolbox
from processing_service.content_intelligence.blocks import (
    COMPARISON_ROWS,
    CYCLE_STAGES,
    FLOW_STEPS,
    MAX_CALLOUT_CHARS,
    MAX_CALLOUT_TITLE_CHARS,
    MAX_CALLOUT_WORDS,
    MAX_CALLOUTS_PER_CHAPTER,
    MAX_COMPARISON_ITEM_CHARS,
    MAX_LABEL_CHARS,
    MAX_PARAGRAPH_CHARS,
    MAX_PARAGRAPH_WORDS,
    MAX_PARAGRAPHS_IN_A_ROW,
    MAX_SHARED_CHARS,
    MAX_STEP_DETAIL_CHARS,
    MAX_TREE_CHILDREN,
    MAX_TREE_LEAF_CHARS,
    MAX_TREE_NODES,
    TREE_BRANCHES,
    BlockInput,
    check_rhythm,
    convert_block,
)
from processing_service.content_intelligence.models import Block, Chapter
from processing_service.content_intelligence.transcript_text import render
from processing_service.domain import ModelReference, Operation, ProcessingError, Transcript

logger = logging.getLogger(__name__)

MAX_CHAPTERS = 8
MIN_CHAPTER_SECONDS = 20.0
BOUNDARY_TOLERANCE_SECONDS = 3.0
BLOCKS_PER_CHAPTER = (2, 8)
MAX_EMIT_FAILURES = 3
MAX_HEADING_CHARS = 80
MAX_REPORTED_PROBLEMS = 8

BLOCK_CATALOG = f"""## Tipos de bloco para emit_chapter (contrato validado)
- paragraph — `text` obrigatório, até {MAX_PARAGRAPH_WORDS} palavras / {MAX_PARAGRAPH_CHARS} caracteres.
  Markdown simples: **negrito** e, se preciso, uma lista curta.
- callout — `variant`, `title` (até {MAX_CALLOUT_TITLE_CHARS} caracteres) e `text` (até
  {MAX_CALLOUT_WORDS} palavras / {MAX_CALLOUT_CHARS} caracteres). Variantes:
  - definition — definição formal de um termo
  - important — ideia central que não pode ser esquecida
  - curiosity — fato curioso ou conexão surpreendente mencionada no vídeo
  - warning — erro comum ou confusão frequente
  - reflection — pergunta de reflexão: `title` é a pergunta e `text` explica por que ela importa
- flow — sequência com setas (A → B → C) para um processo ordenado ou uma cadeia de causa e
  consequência. `title` + `steps` ({FLOW_STEPS[0]} a {FLOW_STEPS[1]}), cada passo com `label`
  (até {MAX_LABEL_CHARS} caracteres) e `detail` opcional (até {MAX_STEP_DETAIL_CHARS}).
- cycle — etapas em círculo com setas, para processos que se repetem. Prefira cycle a flow
  sempre que a última etapa leva de volta à primeira. `title` + `stages` ({CYCLE_STAGES[0]} a
  {CYCLE_STAGES[1]}, até {MAX_LABEL_CHARS} caracteres cada, na ordem do ciclo) + `center`
  opcional: o que o ciclo mantém.
- comparison — dois lados em colunas (antes e depois, prós e contras, A versus B). `title` +
  `columns` (exatamente 2), cada uma com `heading` e `items` ({COMPARISON_ROWS[0]} a
  {COMPARISON_ROWS[1]}, até {MAX_COMPARISON_ITEM_CHARS} caracteres) alinhados linha a linha: o
  item 1 de uma coluna responde ao item 1 da outra. Use `shared` (até {MAX_SHARED_CHARS}) quando
  os dois lados têm algo em comum.
- tree — um conceito central que se divide em partes ou categorias, como um mapa mental.
  `title` + `root` + `branches` ({TREE_BRANCHES[0]} a {TREE_BRANCHES[1]} ramos principais),
  cada ramo com `label` e até {MAX_TREE_CHILDREN} `children` (até {MAX_TREE_LEAF_CHARS}
  caracteres); no máximo {MAX_TREE_NODES} nós no total.
- Rótulos de diagrama são curtos, de poucas palavras, nunca frases inteiras. Não use LaTeX nem
  equações em nenhum bloco."""

SYSTEM_PROMPT = f"""Você transforma a transcrição de um vídeo em capítulos de leitura: texto
corrido e didático, dividido pelos momentos do vídeo. Cada capítulo corresponde a um trecho
contínuo do vídeo e ensina o que foi dito nele. Trabalhe exclusivamente com ferramentas; nunca
responda com texto livre.

## Fluxo (ordem obrigatória)
1. Leia a transcrição inteira, decida onde o assunto muda e chame `publish_outline` uma única
   vez com todos os capítulos.
2. Para cada capítulo, em ordem, chame `emit_chapter` com todos os blocos dele.
3. Depois do último capítulo, chame `finish`.

## Divisão em capítulos
- O primeiro capítulo começa em 0, cada um começa onde o anterior termina e o último termina no
  fim do vídeo. Corte onde o assunto muda, usando os timestamps da transcrição.
- Títulos curtos que digam do que o trecho trata ("Viscoso versus invíscido"), nunca "Parte 1"
  ou "Introdução ao vídeo". O título é exibido automaticamente; não o repita nos blocos.

## Como escrever
- Texto corrido que ensina: parágrafos curtos, frases diretas, uma ideia por parágrafo.
- Coloque em **negrito** cada termo-chave na primeira vez que ele aparece.
- Use somente o que está na transcrição. Não acrescente fatos, números ou exemplos externos.
- Nada de metalinguagem: nunca "neste capítulo", "o vídeo mostra" ou "o palestrante diz".
  Ensine o conteúdo diretamente.
- Trechos confusos podem ser erros de reconhecimento de fala: prefira omitir a inventar.
- Em reuniões e conversas, registre de forma objetiva o que foi discutido e decidido.
- Escreva em português do Brasil.

{BLOCK_CATALOG}

## Ritmo
- Comece cada capítulo com um paragraph e nunca use mais de {MAX_PARAGRAPHS_IN_A_ROW} seguidos.
- Diagramas ficam no meio do texto, logo depois do parágrafo que introduz a ideia. No máximo um
  por capítulo, e só quando o conteúdo tem de fato uma sequência, um ciclo, um contraste ou uma
  hierarquia. Capítulo sem diagrama é normal. Varie os tipos: evite o mesmo tipo de diagrama em
  capítulos seguidos.
- Callouts são destaques, não decoração: no máximo {MAX_CALLOUTS_PER_CHAPTER} por capítulo e
  nunca dois seguidos.
- A reflection fecha o capítulo com uma pergunta que faça pensar sobre o que foi ensinado. Use
  quando fizer sentido, sobretudo em conteúdo de aprendizado, no máximo uma por capítulo.
"""

USER_PROMPT = """Duração do vídeo: {duration:.1f}s. Use entre {low} e {high} capítulos.

Transcrição:

{transcript}

Comece: leia tudo, pense na divisão e chame publish_outline."""


def chapter_bounds(duration_seconds: float) -> tuple[int, int]:
    low = 1 if duration_seconds < 120 else 2
    high = max(1, min(MAX_CHAPTERS, math.ceil(duration_seconds / 60)))
    return low, max(low, high)


class OutlineChapter(BaseModel):
    number: int = Field(description="Sequencial a partir de 1, sem pular")
    title: str = Field(min_length=1, max_length=MAX_HEADING_CHARS)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    focus: str = Field(min_length=1, max_length=200, description="O que o trecho ensina, em 1 frase")


class PublishOutlineArgs(BaseModel):
    chapters: list[OutlineChapter] = Field(min_length=1, max_length=MAX_CHAPTERS)


class EmitChapterArgs(BaseModel):
    number: int
    blocks: list[BlockInput] = Field(min_length=1, max_length=BLOCKS_PER_CHAPTER[1])


class FinishArgs(BaseModel):
    pass


class ChapterToolbox(Toolbox):
    finish_tool = "finish"

    def __init__(self, duration_seconds: float) -> None:
        super().__init__(
            [
                Tool(
                    name="publish_outline",
                    description=(
                        "Publica a divisão do vídeo em capítulos, com título, início e fim de "
                        "cada um. Chame exatamente uma vez, antes de qualquer emit_chapter."
                    ),
                    arguments=PublishOutlineArgs,
                    handler=self._publish_outline,
                ),
                Tool(
                    name="emit_chapter",
                    description=(
                        "Emite todos os blocos de um capítulo, em ordem de leitura. Capítulos "
                        "saem na ordem do sumário. Em caso de erro, corrija os blocos listados e "
                        "chame de novo com o mesmo number."
                    ),
                    arguments=EmitChapterArgs,
                    handler=self._emit_chapter,
                ),
                Tool(
                    name="finish",
                    description="Encerra o trabalho depois que todos os capítulos foram emitidos.",
                    arguments=FinishArgs,
                    handler=self._finish,
                ),
            ]
        )
        self._duration = duration_seconds
        self._bounds = chapter_bounds(duration_seconds)
        self.outline: list[OutlineChapter] = []
        self.emitted: dict[int, tuple[Block, ...]] = {}
        self._failures: dict[int, int] = {}

    def next_step(self) -> str:
        if not self.outline:
            return "chame publish_outline com todos os capítulos."
        pending = self._pending()
        if pending is None:
            return "chame finish."
        return (
            f"chame emit_chapter {pending.number} ({pending.title}, "
            f"{pending.start_seconds:.0f}s–{pending.end_seconds:.0f}s)."
        )

    def chapters(self) -> tuple[Chapter, ...]:
        return tuple(
            Chapter(
                title=item.title,
                start_seconds=item.start_seconds,
                end_seconds=item.end_seconds,
                blocks=self.emitted[item.number],
            )
            for item in self.outline
            if item.number in self.emitted
        )

    def _pending(self) -> OutlineChapter | None:
        return next((item for item in self.outline if item.number not in self.emitted), None)

    def _publish_outline(self, args: PublishOutlineArgs) -> dict[str, Any]:
        if self.outline:
            return {"error": "O sumário já foi publicado; siga com emit_chapter."}
        problems = self._outline_problems(args.chapters)
        if problems:
            return {"error": "Sumário inválido: " + "; ".join(problems[:MAX_REPORTED_PROBLEMS])}
        self.outline = _normalize(args.chapters, self._duration)
        return {"ok": True, "chapters": len(self.outline), "next": self.next_step()}

    def _outline_problems(self, chapters: list[OutlineChapter]) -> list[str]:
        low, high = self._bounds
        problems = []
        if not low <= len(chapters) <= high:
            problems.append(f"use entre {low} e {high} capítulos (recebeu {len(chapters)})")
        if [item.number for item in chapters] != list(range(1, len(chapters) + 1)):
            problems.append("numere os capítulos de 1 a N, em ordem")
        if chapters[0].start_seconds > BOUNDARY_TOLERANCE_SECONDS:
            problems.append("o primeiro capítulo deve começar em 0s")
        if abs(chapters[-1].end_seconds - self._duration) > BOUNDARY_TOLERANCE_SECONDS:
            problems.append(f"o último capítulo deve terminar em {self._duration:.1f}s")
        for previous, current in zip(chapters, chapters[1:]):
            if abs(current.start_seconds - previous.end_seconds) > BOUNDARY_TOLERANCE_SECONDS:
                problems.append(
                    f"o capítulo {current.number} deve começar onde o {previous.number} termina "
                    f"({previous.end_seconds:.1f}s)"
                )
        for item in chapters:
            length = item.end_seconds - item.start_seconds
            if length <= 0:
                problems.append(f"o capítulo {item.number} termina antes de começar")
            elif len(chapters) > 1 and length < MIN_CHAPTER_SECONDS:
                problems.append(
                    f"o capítulo {item.number} tem menos de {MIN_CHAPTER_SECONDS:.0f}s; "
                    "junte-o a um vizinho"
                )
        return problems

    def _emit_chapter(self, args: EmitChapterArgs) -> dict[str, Any]:
        if not self.outline:
            return {"error": "Chame publish_outline antes de emit_chapter."}
        pending = self._pending()
        if pending is None:
            return {"error": "Todos os capítulos já foram emitidos; chame finish."}
        if args.number != pending.number:
            return {"error": f"O próximo capítulo esperado é o {pending.number}."}

        converted: list[Block] = []
        problems: list[str] = []
        for index, block in enumerate(args.blocks, start=1):
            result, issues = convert_block(block)
            if result is None:
                problems.extend(f"blocks[{index}] ({block.kind}): {issue}" for issue in issues)
            else:
                converted.append(result)
        if not problems:
            if len(converted) < BLOCKS_PER_CHAPTER[0]:
                problems.append(
                    f"use entre {BLOCKS_PER_CHAPTER[0]} e {BLOCKS_PER_CHAPTER[1]} blocos"
                )
            problems.extend(check_rhythm(converted))

        if not problems:
            self.emitted[args.number] = tuple(converted)
            return {"ok": True, "next": self.next_step()}

        failures = self._failures[args.number] = self._failures.get(args.number, 0) + 1
        logger.info(
            "Capítulo %s rejeitado na tentativa %s: %s", args.number, failures, "; ".join(problems)
        )
        if failures >= MAX_EMIT_FAILURES and any(block.type == "paragraph" for block in converted):
            self.emitted[args.number] = tuple(converted)
            dropped = len(args.blocks) - len(converted)
            logger.warning("Capítulo %s aceito com %s bloco(s) descartado(s)", args.number, dropped)
            return {
                "ok": True,
                "note": f"Aceito sem {dropped} bloco(s) inválido(s) após tentativas repetidas.",
                "next": self.next_step(),
            }
        return {
            "error": "Blocos inválidos: " + "; ".join(problems[:MAX_REPORTED_PROBLEMS]),
            "attempt": failures,
        }

    def _finish(self, args: FinishArgs) -> dict[str, Any]:
        if not self.outline:
            return {"error": "Nenhum sumário publicado; chame publish_outline."}
        missing = [item.number for item in self.outline if item.number not in self.emitted]
        if missing:
            return {"error": f"Capítulos ainda não emitidos: {missing}."}
        self.finished = True
        return {"ok": True}


def _normalize(chapters: list[OutlineChapter], duration: float) -> list[OutlineChapter]:
    normalized = []
    start = 0.0
    for index, item in enumerate(chapters):
        end = duration if index == len(chapters) - 1 else item.end_seconds
        normalized.append(item.model_copy(update={"start_seconds": start, "end_seconds": end}))
        start = end
    return normalized


class AgentChapterWriter:
    def __init__(self, runner: AgentRunner) -> None:
        self._runner = runner
        self._served: tuple[tuple[str, str], ...] = ()

    @property
    def model(self) -> ModelReference:
        return self._runner.model_reference(Operation.CHAPTERS, self._served)

    def write_chapters(self, transcript: Transcript) -> tuple[Chapter, ...]:
        if not transcript.segments:
            raise ProcessingError(
                "no_speech", "O vídeo não tem fala para dividir em capítulos", retryable=False
            )
        toolbox = ChapterToolbox(transcript.duration_seconds)
        low, high = chapter_bounds(transcript.duration_seconds)
        stats = self._runner.run(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_PROMPT.format(
                duration=transcript.duration_seconds,
                low=low,
                high=high,
                transcript=render(transcript),
            ),
            toolbox=toolbox,
        )
        self._served = stats.served
        chapters = toolbox.chapters()
        if not chapters:
            raise ProcessingError(
                "chapters_incomplete",
                "O agente não entregou capítulos válidos dentro dos limites",
                retryable=True,
            )
        if not toolbox.finished:
            logger.warning("Capítulos parciais: %s de %s", len(chapters), len(toolbox.outline))
        return chapters
