import pytest

from processing_service.content_intelligence.blocks import BlockInput, check_rhythm, convert_block
from processing_service.content_intelligence.models import CalloutBlock, ParagraphBlock

PARAGRAPH = {"kind": "paragraph", "text": "  A **pressão** mantém a divergência nula.  "}
CALLOUT = {
    "kind": "callout",
    "variant": "reflection",
    "title": "Um único termo muda tudo?",
    "text": "Sem viscosidade, desaparece o único mecanismo de suavização.",
}
FLOW = {
    "kind": "flow",
    "title": "Como a pressão age",
    "steps": [
        {"label": "Velocidade desvia"},
        {"label": "Divergência surge", "detail": "O fluido começa a se acumular."},
        {"label": "Pressão ajusta", "detail": "   "},
    ],
}
CYCLE = {
    "kind": "cycle",
    "title": "Como a pressão mantém a restrição",
    "stages": ["Velocidade desvia", "Divergência surge", "Pressão ajusta", "Equilíbrio volta"],
    "center": "Divergência zero",
}
COMPARISON = {
    "kind": "comparison",
    "title": "Duas equações, duas perguntas",
    "columns": [
        {"heading": "Navier-Stokes", "items": ["Mantém o termo viscoso", "Fluido viscoso"]},
        {"heading": "Euler", "items": ["Remove o termo viscoso", "Fluido invíscido"]},
    ],
    "shared": "Ambas carregam a restrição de incompressibilidade",
}
TREE = {
    "kind": "tree",
    "title": "Propriedades do escoamento",
    "root": "Fluido",
    "branches": [
        {"label": "Pressão", "children": ["Mantém o equilíbrio"]},
        {"label": "Viscosidade"},
    ],
}
VALID = {"paragraph": PARAGRAPH, "callout": CALLOUT, "flow": FLOW, "cycle": CYCLE, "comparison": COMPARISON, "tree": TREE}


def convert(fields):
    return convert_block(BlockInput.model_validate(fields))


@pytest.mark.parametrize("kind", VALID)
def test_valid_blocks_are_converted(kind):
    converted, problems = convert(VALID[kind])

    assert problems == []
    assert converted.type == kind


def test_conversion_normalizes_text_and_optional_fields():
    paragraph, _ = convert(PARAGRAPH)
    flow, _ = convert(FLOW)
    comparison, _ = convert(COMPARISON)
    tree, _ = convert(TREE)

    assert paragraph.text == "A **pressão** mantém a divergência nula."
    assert [step.detail for step in flow.steps] == [None, "O fluido começa a se acumular.", None]
    assert [column.heading for column in comparison.columns] == ["Navier-Stokes", "Euler"]
    assert tree.branches[1].children == ()


def comparison_with(**overrides):
    return {**COMPARISON, **overrides}


@pytest.mark.parametrize(
    ("fields", "problem"),
    [
        ({"kind": "paragraph"}, "text é obrigatório"),
        ({"kind": "paragraph", "text": "palavra " * 111}, "texto longo demais (111 palavras"),
        ({"kind": "callout", "title": "T", "text": "x"}, "variant é obrigatório"),
        ({**CALLOUT, "title": "x" * 61}, "title passa de 60 caracteres"),
        ({**CALLOUT, "text": "palavra " * 61}, "texto longo demais (61 palavras"),
        ({**FLOW, "steps": [{"label": "só um"}]}, "steps deve ter entre 2 e 5"),
        (
            {**FLOW, "steps": [{"label": "a"}, {"label": "b", "detail": "x" * 111}]},
            "steps[2].detail passa de 110",
        ),
        ({**FLOW, "title": None}, "title é obrigatório"),
        ({**CYCLE, "stages": ["a", "b"]}, "stages deve ter entre 3 e 6"),
        ({**CYCLE, "stages": ["a", "b", "uma etapa longa demais para caber"]}, "stages[3] passa de 30"),
        ({**CYCLE, "center": "x" * 31}, "center passa de 30"),
        (comparison_with(columns=COMPARISON["columns"][:1]), "columns precisa de exatamente 2"),
        (
            comparison_with(
                columns=[COMPARISON["columns"][0], {"heading": "Euler", "items": ["Só um"]}]
            ),
            "as duas colunas precisam ter o mesmo número de items",
        ),
        (
            comparison_with(
                columns=[{"heading": "A", "items": ["1"]}, {"heading": "B", "items": ["1"]}]
            ),
            "items por coluna deve ter entre 2 e 4",
        ),
        (comparison_with(shared="x" * 91), "shared passa de 90"),
        ({**TREE, "branches": [{"label": "só"}]}, "branches deve ter entre 2 e 5"),
        (
            {**TREE, "branches": [{"label": "a", "children": ["1", "2", "3", "4", "5"]}, {"label": "b"}]},
            "branches[1] tem mais de 4 children",
        ),
        (
            {**TREE, "branches": [{"label": f"r{n}", "children": ["1", "2", "3", "4"]} for n in range(5)]},
            "a árvore tem 26 nós; use no máximo 15",
        ),
        (
            {**TREE, "branches": [{"label": "a", "children": ["x" * 41]}, {"label": "b"}]},
            "branches[1].children[1] passa de 40",
        ),
    ],
    ids=[
        "paragrafo-vazio",
        "paragrafo-longo",
        "callout-sem-variant",
        "callout-titulo-longo",
        "callout-longo",
        "fluxo-curto",
        "fluxo-detalhe-longo",
        "fluxo-sem-titulo",
        "ciclo-curto",
        "ciclo-rotulo-longo",
        "ciclo-centro-longo",
        "comparacao-uma-coluna",
        "comparacao-desalinhada",
        "comparacao-uma-linha",
        "comparacao-comum-longo",
        "arvore-um-ramo",
        "arvore-muitos-filhos",
        "arvore-muitos-nos",
        "arvore-folha-longa",
    ],
)
def test_invalid_blocks_report_problems(fields, problem):
    converted, problems = convert(fields)

    assert converted is None
    assert any(found.startswith(problem) for found in problems), problems


P = ParagraphBlock(text="Parágrafo.")
IMPORTANT = CalloutBlock(variant="important", title="Ideia central", text="Texto.")
REFLECTION = CalloutBlock(variant="reflection", title="E se?", text="Texto.")
DIAGRAM = convert(FLOW)[0]
OTHER_DIAGRAM = convert(CYCLE)[0]


def test_rhythm_accepts_a_well_paced_chapter():
    assert check_rhythm([P, DIAGRAM, P, IMPORTANT, P, REFLECTION]) == []


@pytest.mark.parametrize(
    ("blocks", "problem"),
    [
        ([IMPORTANT, P], "o capítulo deve começar com um paragraph"),
        ([P, DIAGRAM, P, OTHER_DIAGRAM], "use no máximo 1 diagrama"),
        ([P, IMPORTANT, P, IMPORTANT, P, REFLECTION], "use no máximo 2 callouts"),
        ([P, REFLECTION, P, REFLECTION], "use no máximo uma reflection"),
        ([P, P, P, P], "mais de 3 paragraphs seguidos"),
        ([P, IMPORTANT, REFLECTION], "não coloque dois callouts seguidos"),
    ],
    ids=["abre-sem-paragrafo", "dois-diagramas", "tres-callouts", "duas-reflexoes", "paredao", "callouts-colados"],
)
def test_rhythm_problems(blocks, problem):
    assert any(found.startswith(problem) for found in check_rhythm(blocks))
