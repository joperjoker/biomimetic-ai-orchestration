"""Guards for the live-pilot task suite and scorer."""

from pathlib import Path

from pilot_tasks.score_submissions import parse, score_dir
from pilot_tasks.suite import TASK_NAMES, validate


def test_every_reference_passes_its_own_hidden_cases():
    # If a reference fails its own cases, the scoring of real agents is invalid.
    assert all(s == 1.0 for s in validate().values())
    assert len(TASK_NAMES) == 13


def test_parser_extracts_confidence_and_code():
    text = (
        "### TASK: chunk\nCONFIDENCE: 0.5\n```python\n"
        "def chunk(lst, n):\n    return [lst[i:i+n] for i in range(0, len(lst), n)]\n```\n"
    )
    parsed = parse(text)
    assert parsed and parsed[0][0] == "chunk" and parsed[0][1] == 0.5


def test_committed_submissions_score():
    # The committed real submissions score cleanly (every attempt is graded).
    subs = Path("results/live_pilot/submissions")
    if not any(subs.glob("*.txt")):
        return
    records = score_dir(subs)
    assert records
    assert all(0.0 <= r["confidence"] <= 1.0 for r in records)
    assert all(0.0 <= r["pass_fraction"] <= 1.0 for r in records)
