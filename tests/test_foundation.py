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
    for sub in ("signals", "agents", "gates", "orchestrator"):
        assert (ROOT / "src" / sub).is_dir(), f"missing module directory: src/{sub}"


def test_master_context_holds_the_equation():
    text = (ROOT / "claude.md").read_text(encoding="utf-8")
    assert "Binding Energy = (S x C) / L" in text


def test_master_context_holds_the_two_stage_frame():
    text = (ROOT / "claude.md").read_text(encoding="utf-8")
    for term in ("Eligibility", "Activation Energy", "BE >= Ea"):
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


def test_markdown_has_no_forbidden_dashes():
    offenders = []
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        if any(dash in content for dash in FORBIDDEN_DASHES):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"forbidden dash characters found in: {offenders}"
