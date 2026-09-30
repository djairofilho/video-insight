from typing import Literal

from pydantic import BaseModel, Field

from processing_service.content_intelligence.models import (
    DIAGRAM_TYPES,
    Block,
    CalloutBlock,
    CalloutVariant,
    ComparisonColumn,
    ComparisonDiagram,
    CycleDiagram,
    FlowDiagram,
    FlowStep,
    ParagraphBlock,
    TreeBranch,
    TreeDiagram,
)

MAX_PARAGRAPH_WORDS = 110
MAX_PARAGRAPH_CHARS = 750
MAX_CALLOUT_TITLE_CHARS = 60
MAX_CALLOUT_WORDS = 60
MAX_CALLOUT_CHARS = 420
MAX_DIAGRAM_TITLE_CHARS = 60
MAX_LABEL_CHARS = 30
MAX_STEP_DETAIL_CHARS = 110
MAX_COMPARISON_ITEM_CHARS = 40
MAX_SHARED_CHARS = 90
FLOW_STEPS = (2, 5)
CYCLE_STAGES = (3, 6)
COMPARISON_ROWS = (2, 4)
TREE_BRANCHES = (2, 5)
MAX_TREE_CHILDREN = 4
MAX_TREE_NODES = 15
MAX_TREE_LEAF_CHARS = 40
MAX_PARAGRAPHS_IN_A_ROW = 3
MAX_DIAGRAMS_PER_CHAPTER = 1
MAX_CALLOUTS_PER_CHAPTER = 2

BlockKind = Literal["paragraph", "callout", "flow", "cycle", "comparison", "tree"]


class FlowStepInput(BaseModel):
    label: str
    detail: str | None = None


class ColumnInput(BaseModel):
    heading: str
    items: list[str]


class BranchInput(BaseModel):
    label: str
    children: list[str] = Field(default_factory=list)


class BlockInput(BaseModel):
    kind: BlockKind
    text: str | None = Field(default=None, description="paragraph e callout: texto em Markdown")
    title: str | None = Field(default=None, description="callout e diagramas: título")
    variant: CalloutVariant | None = Field(default=None, description="callout: tipo do destaque")
    steps: list[FlowStepInput] | None = Field(default=None, description="flow: passos em ordem")
    stages: list[str] | None = Field(default=None, description="cycle: etapas na ordem do ciclo")
    center: str | None = Field(default=None, description="cycle: o que o ciclo mantém")
    columns: list[ColumnInput] | None = Field(default=None, description="comparison: 2 colunas")
    shared: str | None = Field(default=None, description="comparison: o que as colunas têm em comum")
    root: str | None = Field(default=None, description="tree: conceito central")
    branches: list[BranchInput] | None = Field(default=None, description="tree: ramos")


def convert_block(block: BlockInput) -> tuple[Block | None, list[str]]:
    converter = _CONVERTERS[block.kind]
    problems: list[str] = []
    converted = converter(block, problems)
    return (None, problems) if problems else (converted, [])


def check_rhythm(blocks: list[Block]) -> list[str]:
    problems = []
    if blocks and blocks[0].type != "paragraph":
        problems.append("o capítulo deve começar com um paragraph")
    diagrams = sum(block.type in DIAGRAM_TYPES for block in blocks)
    if diagrams > MAX_DIAGRAMS_PER_CHAPTER:
        problems.append(f"use no máximo {MAX_DIAGRAMS_PER_CHAPTER} diagrama por capítulo")
    callouts = [block for block in blocks if isinstance(block, CalloutBlock)]
    if len(callouts) > MAX_CALLOUTS_PER_CHAPTER:
        problems.append(f"use no máximo {MAX_CALLOUTS_PER_CHAPTER} callouts por capítulo")
    if sum(callout.variant == "reflection" for callout in callouts) > 1:
        problems.append("use no máximo uma reflection por capítulo")
    run = 0
    for index, block in enumerate(blocks):
        run = run + 1 if block.type == "paragraph" else 0
        if run > MAX_PARAGRAPHS_IN_A_ROW:
            problems.append(f"mais de {MAX_PARAGRAPHS_IN_A_ROW} paragraphs seguidos")
            break
        if index and block.type == "callout" and blocks[index - 1].type == "callout":
            problems.append("não coloque dois callouts seguidos")
            break
    return problems


def _paragraph(block: BlockInput, problems: list[str]) -> ParagraphBlock | None:
    text = _required(block.text, "text", problems)
    if text:
        _limit_words(text, MAX_PARAGRAPH_WORDS, MAX_PARAGRAPH_CHARS, problems, "divida em dois paragraphs")
        return ParagraphBlock(text=text)
    return None


def _callout(block: BlockInput, problems: list[str]) -> CalloutBlock | None:
    if block.variant is None:
        problems.append("variant é obrigatório")
    title = _label(block.title, "title", MAX_CALLOUT_TITLE_CHARS, problems)
    text = _required(block.text, "text", problems)
    if text:
        _limit_words(text, MAX_CALLOUT_WORDS, MAX_CALLOUT_CHARS, problems, "encurte o destaque")
    if problems:
        return None
    return CalloutBlock(variant=block.variant, title=title, text=text)


def _flow(block: BlockInput, problems: list[str]) -> FlowDiagram | None:
    title = _label(block.title, "title", MAX_DIAGRAM_TITLE_CHARS, problems)
    steps = block.steps or []
    _count(len(steps), FLOW_STEPS, "steps", problems)
    converted = []
    for index, step in enumerate(steps, start=1):
        label = _label(step.label, f"steps[{index}].label", MAX_LABEL_CHARS, problems)
        detail = (step.detail or "").strip() or None
        if detail and len(detail) > MAX_STEP_DETAIL_CHARS:
            problems.append(f"steps[{index}].detail passa de {MAX_STEP_DETAIL_CHARS} caracteres")
        converted.append((label, detail))
    if problems:
        return None
    return FlowDiagram(
        title=title, steps=tuple(FlowStep(label=label, detail=detail) for label, detail in converted)
    )


def _cycle(block: BlockInput, problems: list[str]) -> CycleDiagram | None:
    title = _label(block.title, "title", MAX_DIAGRAM_TITLE_CHARS, problems)
    stages = block.stages or []
    _count(len(stages), CYCLE_STAGES, "stages", problems)
    labels = [
        _label(stage, f"stages[{index}]", MAX_LABEL_CHARS, problems)
        for index, stage in enumerate(stages, start=1)
    ]
    center = _optional_label(block.center, "center", MAX_LABEL_CHARS, problems)
    if problems:
        return None
    return CycleDiagram(title=title, stages=tuple(labels), center=center)


def _comparison(block: BlockInput, problems: list[str]) -> ComparisonDiagram | None:
    title = _label(block.title, "title", MAX_DIAGRAM_TITLE_CHARS, problems)
    columns = block.columns or []
    if len(columns) != 2:
        problems.append(f"columns precisa de exatamente 2 colunas (recebeu {len(columns)})")
        return None
    rows = {len(column.items) for column in columns}
    if len(rows) != 1:
        problems.append("as duas colunas precisam ter o mesmo número de items, alinhados linha a linha")
    _count(max(rows), COMPARISON_ROWS, "items por coluna", problems)
    converted = []
    for side, column in enumerate(columns, start=1):
        heading = _label(column.heading, f"columns[{side}].heading", MAX_LABEL_CHARS, problems)
        items = tuple(
            _label(item, f"columns[{side}].items[{row}]", MAX_COMPARISON_ITEM_CHARS, problems)
            for row, item in enumerate(column.items, start=1)
        )
        converted.append((heading, items))
    shared = _optional_label(block.shared, "shared", MAX_SHARED_CHARS, problems)
    if problems:
        return None
    left, right = (ComparisonColumn(heading=heading, items=items) for heading, items in converted)
    return ComparisonDiagram(title=title, columns=(left, right), shared=shared)


def _tree(block: BlockInput, problems: list[str]) -> TreeDiagram | None:
    title = _label(block.title, "title", MAX_DIAGRAM_TITLE_CHARS, problems)
    root = _label(block.root, "root", MAX_LABEL_CHARS, problems)
    branches = block.branches or []
    _count(len(branches), TREE_BRANCHES, "branches", problems)
    converted = []
    for index, branch in enumerate(branches, start=1):
        label = _label(branch.label, f"branches[{index}].label", MAX_LABEL_CHARS, problems)
        if len(branch.children) > MAX_TREE_CHILDREN:
            problems.append(f"branches[{index}] tem mais de {MAX_TREE_CHILDREN} children")
        children = tuple(
            _label(child, f"branches[{index}].children[{position}]", MAX_TREE_LEAF_CHARS, problems)
            for position, child in enumerate(branch.children, start=1)
        )
        converted.append((label, children))
    nodes = 1 + sum(1 + len(children) for _, children in converted)
    if nodes > MAX_TREE_NODES:
        problems.append(f"a árvore tem {nodes} nós; use no máximo {MAX_TREE_NODES}")
    if problems:
        return None
    return TreeDiagram(
        title=title,
        root=root,
        branches=tuple(TreeBranch(label=label, children=children) for label, children in converted),
    )


def _required(value: str | None, field: str, problems: list[str]) -> str:
    text = (value or "").strip()
    if not text:
        problems.append(f"{field} é obrigatório")
    return text


def _label(value: str | None, field: str, limit: int, problems: list[str]) -> str:
    text = _required(value, field, problems)
    if len(text) > limit:
        problems.append(f"{field} passa de {limit} caracteres ({len(text)}); use poucas palavras")
    return text


def _optional_label(value: str | None, field: str, limit: int, problems: list[str]) -> str | None:
    text = (value or "").strip()
    if len(text) > limit:
        problems.append(f"{field} passa de {limit} caracteres ({len(text)})")
    return text or None


def _limit_words(text: str, words: int, chars: int, problems: list[str], hint: str) -> None:
    count = len(text.split())
    if count > words or len(text) > chars:
        problems.append(
            f"texto longo demais ({count} palavras / {len(text)} caracteres; máximo {words} / {chars}) — {hint}"
        )


def _count(amount: int, bounds: tuple[int, int], field: str, problems: list[str]) -> None:
    low, high = bounds
    if not low <= amount <= high:
        problems.append(f"{field} deve ter entre {low} e {high} elementos (recebeu {amount})")


_CONVERTERS = {
    "paragraph": _paragraph,
    "callout": _callout,
    "flow": _flow,
    "cycle": _cycle,
    "comparison": _comparison,
    "tree": _tree,
}
