from typing import Annotated, Literal

from pydantic import Field

from processing_service.domain import FrozenModel

ContentKind = Literal["meeting", "lecture", "tutorial", "interview", "presentation", "other"]
CalloutVariant = Literal["definition", "important", "curiosity", "warning", "reflection"]


class Summary(FrozenModel):
    content_kind: ContentKind
    text: str = Field(min_length=1)


class ParagraphBlock(FrozenModel):
    type: Literal["paragraph"] = "paragraph"
    text: str = Field(min_length=1)


class CalloutBlock(FrozenModel):
    type: Literal["callout"] = "callout"
    variant: CalloutVariant
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)


class FlowStep(FrozenModel):
    label: str = Field(min_length=1)
    detail: str | None = None


class FlowDiagram(FrozenModel):
    type: Literal["flow"] = "flow"
    title: str = Field(min_length=1)
    steps: tuple[FlowStep, ...] = Field(min_length=2)


class CycleDiagram(FrozenModel):
    type: Literal["cycle"] = "cycle"
    title: str = Field(min_length=1)
    stages: tuple[str, ...] = Field(min_length=3)
    center: str | None = None


class ComparisonColumn(FrozenModel):
    heading: str = Field(min_length=1)
    items: tuple[str, ...] = Field(min_length=1)


class ComparisonDiagram(FrozenModel):
    type: Literal["comparison"] = "comparison"
    title: str = Field(min_length=1)
    columns: tuple[ComparisonColumn, ComparisonColumn]
    shared: str | None = None


class TreeBranch(FrozenModel):
    label: str = Field(min_length=1)
    children: tuple[str, ...] = ()


class TreeDiagram(FrozenModel):
    type: Literal["tree"] = "tree"
    title: str = Field(min_length=1)
    root: str = Field(min_length=1)
    branches: tuple[TreeBranch, ...] = Field(min_length=2)


Block = Annotated[
    ParagraphBlock | CalloutBlock | FlowDiagram | CycleDiagram | ComparisonDiagram | TreeDiagram,
    Field(discriminator="type"),
]

DIAGRAM_TYPES = {"flow", "cycle", "comparison", "tree"}


class Chapter(FrozenModel):
    title: str = Field(min_length=1)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    blocks: tuple[Block, ...] = Field(min_length=1)


class ChapterList(FrozenModel):
    chapters: tuple[Chapter, ...]
