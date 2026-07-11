"""The Paper 2 head-to-head harness: four routing policies over a task stream."""

import json

from cta.headtohead import (
    POLICIES,
    Task,
    head_to_head,
    run_policy,
    sim_solver,
    summarise,
    write_report,
)
from cta.wrappers import Model


def _models():
    return [
        Model(name="haiku", tier="economy"),
        Model(name="sonnet", tier="standard"),
        Model(name="opus", tier="premium"),
    ]


# A stream of easy and hard tasks. A cheap model clears easy tasks but fails hard
# ones; only the frontier clears the hard ones.
def _stream():
    tasks = [Task(name=f"easy{i}", task_type="easy") for i in range(6)]
    tasks += [Task(name=f"hard{i}", task_type="hard") for i in range(6)]
    return tasks


_CAPABILITY = {"haiku": 0.5, "sonnet": 0.8, "opus": 0.95}
# easy tasks: any model passes; hard tasks: only opus passes.
_DIFFICULTY = {f"easy{i}": 0.4 for i in range(6)} | {f"hard{i}": 0.9 for i in range(6)}

# Calibration data a real deployment has from prior runs: haiku reliable on easy,
# unreliable on hard; opus reliable on both.
_WARM = {
    "haiku": {"easy": 0.98, "hard": 0.05},
    "sonnet": {"easy": 0.98, "hard": 0.10},
    "opus": {"easy": 0.99, "hard": 0.98},
}


def _solver():
    return sim_solver(_CAPABILITY, _DIFFICULTY)


def test_all_policies_reported_with_cis():
    res = head_to_head(_stream(), _solver(), _models(), warm_start=_WARM)
    assert set(res["policies"]) == set(POLICIES)
    for p in POLICIES:
        s = res["policies"][p]
        assert s["completion_lo"] <= s["completion"] <= s["completion_hi"]
        assert s["n"] == 12


def test_corrected_matches_frontier_completion_below_frontier_cost():
    res = head_to_head(_stream(), _solver(), _models(), warm_start=_WARM)
    cta = res["policies"]["cta_corrected"]
    frontier = res["policies"]["always_frontier"]
    # Corrected routing sends hard tasks to the frontier and easy tasks to the
    # cheap model: it retains frontier completion.
    assert cta["completion"] == frontier["completion"] == 1.0
    # ...but at a strictly lower cost, because easy tasks go cheap.
    assert cta["total_cost_usd"] < frontier["total_cost_usd"]
    assert res["comparison"]["cost_saving_vs_frontier"] > 1.0


def test_correction_beats_naive_self_report():
    res = head_to_head(_stream(), _solver(), _models(), warm_start=_WARM)
    cta = res["policies"]["cta_corrected"]
    naive = res["policies"]["naive_self_report"]
    # Naive trusts the cheap model's high raw bid and routes hard tasks to it too,
    # so it fails every hard task; the correction escalates them.
    assert naive["completion"] < cta["completion"]
    assert res["comparison"]["completion_gain_vs_naive"] > 0.0


def test_single_cheapest_fails_the_hard_half():
    outcomes = run_policy("single_cheapest", _stream(), _solver(), _models())
    s = summarise(outcomes)
    assert all(o.model == "haiku" for o in outcomes)
    assert s["completion"] == 0.5  # passes the six easy, fails the six hard


def test_probe_mode_charges_overhead_only_to_eliciting_policies():
    res = head_to_head(
        _stream(), _solver(), _models(), warm_start=_WARM, probe_turns_per_task=1
    )
    # Eliciting policies pay a probe cost; static ones do not.
    assert res["policies"]["cta_corrected"]["probe_cost_usd"] > 0.0
    assert res["policies"]["naive_self_report"]["probe_cost_usd"] > 0.0
    assert res["policies"]["always_frontier"]["probe_cost_usd"] == 0.0
    assert res["policies"]["single_cheapest"]["probe_cost_usd"] == 0.0
    # The overhead is a small fraction of the total, not the dominant cost.
    assert 0.0 < res["comparison"]["probe_overhead_fraction"] < 0.5


def test_deterministic():
    a = head_to_head(_stream(), _solver(), _models(), warm_start=_WARM)
    b = head_to_head(_stream(), _solver(), _models(), warm_start=_WARM)
    assert a == b


def test_write_report_emits_summary_results_and_figure(tmp_path):
    res = head_to_head(_stream(), _solver(), _models(), warm_start=_WARM)
    paths = write_report(res, tmp_path)
    assert paths["summary"].exists() and paths["results"].exists()
    assert paths["figure"].exists()
    loaded = json.loads(paths["summary"].read_text())
    assert loaded["policies"]["cta_corrected"]["completion"] == 1.0
    md = paths["results"].read_text()
    assert "CTA (corrected)" in md and "Cost saving versus always-frontier" in md
    svg = paths["figure"].read_text()
    assert svg.startswith("<svg") and "completion" in svg
