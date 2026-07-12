"""The live ACP-broker vignette: routing preview and real-solution scoring."""

from pathlib import Path

import pytest

from pilot_tasks.vignette import TASKS, _score, preview

_HAS_DATA = Path("results/vignette/is_match.txt").exists()


def test_preview_routes_cheap_by_default_and_escalates_is_match():
    routed = preview()
    assert routed["fraction_to_decimal"] == "haiku"
    assert routed["multiply_strings"] == "haiku"
    assert routed["word_break"] == "haiku"
    # is_match is the one task Haiku is unreliable on; its corrected bid falls
    # below the barrier, so the broker escalates.
    assert routed["is_match"] == "sonnet"


@pytest.mark.skipif(not _HAS_DATA, reason="vignette solutions not present")
def test_saved_solutions_pass_the_hidden_tests():
    for task in TASKS:
        passed, frac = _score(task)
        assert passed, f"{task} scored {frac:.2f}, expected a full pass"
