"""Phase 2C: the leave-one-replicate-out head-to-head replay over ladder data."""

from pilot_tasks.expert_suite import TASK_NAMES
from pilot_tasks.headtohead import _complete_replicates, _index, _run_replay


def _synthetic_table():
    """Four replicates x three models over the real task names. Haiku fails the
    first task every time and clears the rest; sonnet/opus clear everything. Stated
    confidence is uniformly high (Claude is well-calibrated-to-overconfident), so a
    naive self-report router cannot tell the failing task apart without the record."""
    records = []
    hard = TASK_NAMES[0]
    for k in range(1, 5):
        for model in ("haiku", "sonnet", "opus"):
            for task in TASK_NAMES:
                passed = not (model == "haiku" and task == hard)
                records.append({
                    "condition": "bare",
                    "agent": f"{model}__bare__{k}",
                    "model": model,
                    "task": task,
                    "confidence": 0.9,
                    "passed": passed,
                })
    return _index(records)


def test_index_keys_by_replicate_number():
    table = _index([{
        "condition": "bare", "agent": "haiku__bare__3", "model": "haiku",
        "task": TASK_NAMES[0], "confidence": 0.9, "passed": True,
    }])
    assert "3" in table and "haiku" in table["3"]


def test_complete_replicates_requires_all_models_and_tasks():
    table = _synthetic_table()
    assert _complete_replicates(table) == ["1", "2", "3", "4"]


def test_replay_ranks_policies_as_expected():
    result = _run_replay(_synthetic_table())
    pol = result["policies"]
    # Frontier clears every task; cheapest fails the one task haiku cannot do.
    assert pol["always_frontier"]["completion"] == 1.0
    assert pol["single_cheapest"]["completion"] < 1.0
    # The correction escalates exactly that task, so it beats naive/cheapest...
    assert pol["cta_corrected"]["completion"] > pol["single_cheapest"]["completion"]
    assert result["comparison"]["completion_gain_vs_naive"] > 0.0
    # ...while staying far below frontier cost.
    assert pol["cta_corrected"]["cost_usd"] < pol["always_frontier"]["cost_usd"]
    assert result["comparison"]["cost_saving_vs_frontier"] > 1.0


def test_replay_is_deterministic():
    table = _synthetic_table()
    assert _run_replay(table) == _run_replay(table)
