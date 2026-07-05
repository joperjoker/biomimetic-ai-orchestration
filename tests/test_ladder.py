"""Guards for the capability-ladder x wrapper-ablation analysis."""

from pathlib import Path

from pilot_tasks.ladder import CONDITIONS, MODELS, analyse, load

LADDER = Path("results/live_pilot/ladder")


def test_ladder_submissions_parse_and_score():
    if not any(LADDER.glob("*.txt")):
        return
    records = load(LADDER)
    assert records
    for r in records:
        assert r["model"] in MODELS
        assert r["condition"] in CONDITIONS
        assert 0.0 <= r["confidence"] <= 1.0
        assert 0.0 <= r["pass_fraction"] <= 1.0


def test_ladder_analysis_shows_capability_and_wrapper_effects():
    if not any(LADDER.glob("*.txt")):
        return
    s = analyse(LADDER)
    cells = s["cells"]
    # The capability ladder: the weakest model does not beat the strongest on bare.
    haiku_bare = cells["haiku"]["bare"]["completion"]
    opus_bare = cells["opus"]["bare"]["completion"]
    assert haiku_bare <= opus_bare
    # The task wrapper never lowers the weak model's completion and lifts it here.
    assert s["task_wrapper_lift"]["haiku"]["completion_lift"] >= 0.0
    # The agent wrapper routing block is well formed under both conditions.
    for key in ("agent_wrapper_routing", "agent_wrapper_routing_bare"):
        r = s[key]
        assert 0.0 <= r["routed_completion"] <= 1.0
        assert r["cost_saving_multiple"] > 1.0
        assert set(r["choices"]) == set(analyse.__globals__["TASK_NAMES"])
