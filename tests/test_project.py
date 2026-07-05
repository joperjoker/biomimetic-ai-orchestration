"""Guards for the miniquery project suite and the assembly analysis."""

from pathlib import Path

from pilot_tasks.project import MODELS, analyse
from pilot_tasks.project_suite import MODULE_NAMES, _selftest, validate

PROJECT = Path("results/live_pilot/project")


def test_project_references_valid():
    _selftest()
    assert all(v == 1.0 for v in validate().values())
    assert len(MODULE_NAMES) == 5


def test_project_wrappers_and_assembly():
    if not any(PROJECT.glob("*.txt")):
        return
    s = analyse(PROJECT)
    # The task wrapper never lowers project completion and lifts it here.
    for m in MODELS:
        if m in s["task_wrapper_lift"]:
            assert s["task_wrapper_lift"][m]["completion_lift"] >= 0.0
    # The agent-wrapper assembly is well formed and the wrapped assembly is at
    # least as complete as the bare assembly.
    aw, ab = s["assembly_wrapped"], s["assembly_bare"]
    if aw and ab:
        assert aw["assembled_completion"] >= ab["assembled_completion"]
        assert aw["cost_saving_multiple"] > 1.0
        assert set(aw["choices"]) == set(MODULE_NAMES)
