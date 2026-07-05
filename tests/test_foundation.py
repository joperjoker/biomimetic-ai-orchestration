"""Foundation guard tests.

These tests protect the foundation of the project: they confirm the expected
structure and key documents are present, and they enforce the project style
constraint that forbids dash variants in tracked Markdown. They are intended to
be replaced or joined by behavioural tests once the modules are implemented.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Dash variants that the style constraint forbids in prose:
# en dash, em dash, figure dash, horizontal bar.
FORBIDDEN_DASHES = ["–", "—", "‒", "―"]


def test_key_documents_exist():
    for name in ("README.md", "claude.md", "CONTRIBUTING.md", "pyproject.toml"):
        assert (ROOT / name).is_file(), f"missing expected file: {name}"


def test_module_layout_exists():
    pkg = ROOT / "src" / "cta"
    assert pkg.is_dir(), "missing package directory: src/cta"
    for module in ("scoring", "engine", "harness", "baselines", "store"):
        assert (pkg / f"{module}.py").is_file(), f"missing module: src/cta/{module}.py"
    assert (pkg / "autoresearch" / "__init__.py").is_file(), "missing cta.autoresearch"


def test_master_context_holds_the_equation():
    text = (ROOT / "claude.md").read_text(encoding="utf-8")
    assert "Binding Energy = (c x C_tilde) / L" in text


def test_master_context_holds_the_two_stage_frame():
    text = (ROOT / "claude.md").read_text(encoding="utf-8")
    for term in ("Eligibility", "Activation Energy", "c >= Ea"):
        assert term in text, f"missing two-stage selection term: {term}"


def test_paper_holds_formal_framework():
    text = (ROOT / "docs" / "paper.md").read_text(encoding="utf-8")
    for term in ("Formal framework", "P_fire", "W_coord"):
        assert term in text, f"missing formal-framework marker: {term}"


def test_architecture_document_present():
    path = ROOT / "docs" / "architecture.md"
    assert path.is_file(), "missing docs/architecture.md"
    text = path.read_text(encoding="utf-8")
    for term in ("Experimental Architecture", "atomic claim", "metric to measurement"):
        assert term.lower() in text.lower(), f"missing architecture marker: {term}"


def test_measurable_model_present_and_compatibility_framing():
    measures = ROOT / "docs" / "measures.md"
    assert measures.is_file(), "missing docs/measures.md"
    text = measures.read_text(encoding="utf-8")
    for term in ("compatibility", "wrapper", "role", "skill", "prompt"):
        assert term.lower() in text.lower(), f"measures.md missing: {term}"
    paper = (ROOT / "docs" / "paper.md").read_text(encoding="utf-8")
    assert "c >= Ea" in paper, "activation should be on compatibility (c >= Ea)"


def test_paper_has_pull_based_baseline_and_heterogeneity():
    text = (ROOT / "docs" / "paper.md").read_text(encoding="utf-8")
    assert "pull-based" in text.lower(), "missing the pull-based baseline"
    for marker in ("RQ6", "H6"):
        assert marker in text, f"missing hypothesis or question marker: {marker}"


def test_recursive_language_models_named_correctly():
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8").lower()
        assert "recursive learning model" not in text, (
            f"misnomer 'recursive learning model' in {path.relative_to(ROOT)}; "
            "use 'Recursive Language Models'"
        )
    arch = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert "Context and memory layer" in arch, "missing context/memory layer component"


def test_markdown_has_no_forbidden_dashes():
    offenders = []
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        if any(dash in content for dash in FORBIDDEN_DASHES):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"forbidden dash characters found in: {offenders}"
