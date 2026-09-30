import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from processing_service.content_intelligence.agent import AgentRunner, Tool, Toolbox
from processing_service.content_intelligence.models import ContentKind, Summary
from processing_service.content_intelligence.transcript_text import render
from processing_service.domain import ModelReference, Operation, ProcessingError, Transcript

logger = logging.getLogger(__name__)

MIN_WORDS = 50
MAX_WORDS = 350
LEARNING_KINDS = {"lecture", "tutorial"}
META_TEXT = re.compile(
    r"\b(?:(?:n?este|n?esse|o|no|do)\s+vídeo|(?:n?esta|n?essa)\s+aula"
    r"|o\s+(?:palestrante|apresentador|professor|narrador)\s+(?:diz|fala|explica|mostra|afirma))\b",
    re.IGNORECASE,
)

STYLE_GUIDES: dict[str, str] = {
    "meeting": (
        "Reunião: organize em tópicos. Abra com uma frase de contexto. Depois use rótulos em "
        "negrito como **Decisões**, **Pendências e responsáveis** e **Pontos discutidos**, cada "
        "um seguido de uma lista curta. Omita rótulos sem conteúdo no vídeo."
    ),
    "lecture": (
        "Aula: misture tópicos e bullets. Abra com 2 ou 3 frases de visão geral. Depois agrupe "
        "o conteúdo em 2 a 4 tópicos com títulos `###`, cada um com bullets curtos. Coloque o "
        "**termo-chave em negrito** no início do bullet que o define."
    ),
    "tutorial": (
        "Tutorial: abra com uma frase sobre o que se aprende a fazer. Use um tópico `###` com os "
        "passos numerados na ordem do vídeo e outro com dicas ou cuidados em bullets. Destaque "
        "em **negrito** os comandos, ferramentas e termos essenciais."
    ),
    "interview": (
        "Entrevista: um parágrafo curto dizendo quem fala e sobre o quê, seguido de bullets com "
        "as principais ideias e posições defendidas."
    ),
    "presentation": (
        "Apresentação ou palestra: um parágrafo com a tese central, bullets com os argumentos e "
        "dados que a sustentam e uma frase final com a conclusão ou chamada à ação."
    ),
    "other": "Um parágrafo curto com a ideia geral, seguido de bullets com os pontos principais.",
}

SYSTEM_PROMPT = f"""Você escreve o resumo de um vídeo a partir da transcrição com timestamps.
Trabalhe exclusivamente com ferramentas; nunca responda com texto livre.

## Fluxo
1. Leia a transcrição inteira e chame `classify_content` com o tipo de conteúdo. A resposta
   traz o guia de formato para esse tipo.
2. Escreva o resumo seguindo o guia e chame `submit_summary`. Se houver erros de validação,
   corrija exatamente o que foi apontado e chame `submit_summary` de novo.

## Regras
- Use somente informações da transcrição. Não acrescente fatos, exemplos ou opiniões externas.
- Escreva em português do Brasil, em Markdown simples, sem blocos de código e sem título `#`.
- Entre {MIN_WORDS} e {MAX_WORDS} palavras. Seja direto: nada de "neste vídeo" ou "o vídeo
  fala sobre"; vá ao conteúdo.
- Trechos confusos da transcrição podem ser erros de reconhecimento de fala: prefira omitir a
  inventar uma interpretação.
"""


class ClassifyContentArgs(BaseModel):
    content_kind: ContentKind = Field(
        description=(
            "meeting = reunião de trabalho; lecture = aula ou explicação de conceitos; "
            "tutorial = passo a passo prático; interview = entrevista ou conversa; "
            "presentation = palestra, pitch ou apresentação; other = qualquer outro caso"
        )
    )
    rationale: str = Field(min_length=1, max_length=300, description="Justificativa em uma frase")


class SubmitSummaryArgs(BaseModel):
    markdown: str = Field(min_length=1, description="Resumo completo em Markdown")


class SummaryToolbox(Toolbox):
    finish_tool = "submit_summary"

    def __init__(self) -> None:
        super().__init__(
            [
                Tool(
                    name="classify_content",
                    description=(
                        "Define o tipo de conteúdo do vídeo e devolve o guia de formato do "
                        "resumo. Chame antes de submit_summary; pode chamar de novo para "
                        "reclassificar."
                    ),
                    arguments=ClassifyContentArgs,
                    handler=self._classify,
                ),
                Tool(
                    name="submit_summary",
                    description=(
                        "Entrega o resumo final em Markdown. É validado; em caso de erro, "
                        "corrija os pontos listados e envie de novo."
                    ),
                    arguments=SubmitSummaryArgs,
                    handler=self._submit,
                ),
            ]
        )
        self.content_kind: str | None = None
        self.result: Summary | None = None

    def next_step(self) -> str:
        if self.content_kind is None:
            return "chame classify_content."
        return "chame submit_summary com o resumo."

    def _classify(self, args: ClassifyContentArgs) -> dict[str, Any]:
        self.content_kind = args.content_kind
        return {"ok": True, "style_guide": STYLE_GUIDES[args.content_kind]}

    def _submit(self, args: SubmitSummaryArgs) -> dict[str, Any]:
        if self.content_kind is None:
            return {"error": "Chame classify_content antes de submit_summary."}
        problems = validate_summary(args.markdown, self.content_kind)
        if problems:
            logger.info("Resumo rejeitado: %s", "; ".join(problems))
            return {"error": "Resumo inválido: " + "; ".join(problems)}
        self.result = Summary(content_kind=self.content_kind, text=args.markdown.strip())
        self.finished = True
        return {"ok": True}


def validate_summary(markdown: str, content_kind: str) -> list[str]:
    problems = []
    words = len(markdown.split())
    if not MIN_WORDS <= words <= MAX_WORDS:
        problems.append(f"tem {words} palavras; use entre {MIN_WORDS} e {MAX_WORDS}")
    if "```" in markdown:
        problems.append("remova blocos de código")
    if re.search(r"^#\s", markdown, flags=re.MULTILINE):
        problems.append("não use título de nível 1 (#)")
    if not re.search(r"^\s*(?:[-*]|\d+\.)\s+\S", markdown, flags=re.MULTILINE):
        problems.append("inclua ao menos uma lista com marcadores ou numerada")
    if content_kind in LEARNING_KINDS and "**" not in markdown:
        problems.append("destaque os termos-chave em **negrito**")
    meta = META_TEXT.search(markdown)
    if meta:
        problems.append(
            f"remova o meta-texto '{meta.group(0)}': não fale do vídeo, apresente o conteúdo direto"
        )
    return problems


class AgentSummarizer:
    def __init__(self, runner: AgentRunner) -> None:
        self._runner = runner
        self._served: tuple[tuple[str, str], ...] = ()

    @property
    def model(self) -> ModelReference:
        return self._runner.model_reference(Operation.SUMMARY, self._served)

    def summarize(self, transcript: Transcript) -> Summary:
        if not transcript.segments:
            raise ProcessingError("no_speech", "O vídeo não tem fala para resumir", retryable=False)
        toolbox = SummaryToolbox()
        stats = self._runner.run(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"Transcrição do vídeo:\n\n{render(transcript)}",
            toolbox=toolbox,
        )
        self._served = stats.served
        if toolbox.result is None:
            raise ProcessingError(
                "summary_incomplete",
                "O agente não entregou um resumo válido dentro dos limites",
                retryable=True,
            )
        return toolbox.result
