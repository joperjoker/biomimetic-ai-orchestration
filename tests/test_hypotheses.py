"""Tests for the H3, H4, H5, H7, and H8 evaluations."""

from dataclasses import replace

from cta.harness import (
    CellParams,
    calibration_sweep,
    feasibility_check,
    gate_ablation,
    recovery_vs_spread,
    reduction_vs_recall,
    safety_ablation,
    stability_grid,
    track_record_sweep,
)


def test_feasibility_labelling_is_correct():
    base = CellParams(n_agents=30, n_tasks=10, n_domains=4, heterogeneity=0.8)
    res = feasibility_check(base, seed=0)
    # Tasks requiring an absent tool are infeasible; unreachable Ea stalls them.
    assert res["infeasible_recall"] == 1.0
    assert res["stalled_recall"] == 1.0


def test_gate_ablation_is_quality_neutral():
    base = CellParams(n_agents=60, n_tasks=48, n_domains=4, heterogeneity=0.8)
    res = gate_ablation(base, seeds=4, unreliable_fraction=0.5)
    on = sum(res["gate_on_quality"]) / len(res["gate_on_quality"])
    off = sum(res["gate_off_quality"]) / len(res["gate_off_quality"])
    # With reliability-weighted selection the winner already has a good record, so
    # the reliability gate is roughly quality-neutral: its value is safety (H4),
    # not quality. The two should be close either way.
    assert abs(on - off) < 0.03


def test_calibration_sweep_recovers_completion():
    base = CellParams(n_agents=60, n_tasks=48, n_domains=4, heterogeneity=0.8)
    sweep = calibration_sweep(base, seeds=3, bias_values=(0.0, 0.4))
    assert set(sweep.keys()) == {"raw", "reliability", "true"}
    raw_top = sweep["raw"][-1]
    rel_top = sweep["reliability"][-1]
    # The track-record correction completes more tasks than the raw self-report.
    assert rel_top["completion_rate"] > raw_top["completion_rate"]
    # Winners over-report under raw self-selection (positive overconfidence gap).
    assert raw_top["overconfidence_gap"] > 0.0
    assert len(raw_top["completion_values"]) == 3


def test_recovery_grows_with_competence_spread():
    base = CellParams(n_agents=60, n_tasks=48, n_domains=4, heterogeneity=0.8)
    sweep = recovery_vs_spread(base, seeds=4, lows=(0.7, 0.1))
    narrow, wide = sweep[0], sweep[-1]
    # A wider competence spread (lower floor) gives the correction more to recover.
    assert wide["recovery"] > narrow["recovery"]


def test_violation_reduction_grows_with_recall():
    base = CellParams(n_agents=60, n_tasks=48, n_domains=4, heterogeneity=0.8)
    sweep = reduction_vs_recall(base, seeds=4, recalls=(0.5, 1.0))
    assert sweep[-1]["reduction"] > sweep[0]["reduction"]
    assert sweep[-1]["reduction"] >= 0.999  # perfect recall blocks everything


def test_calibration_recovers_under_latent_family():
    # The calibration finding (H8) must hold under a structurally different
    # generator, not only the domains structure.
    base = replace(
        CellParams(n_agents=60, n_tasks=48, n_domains=4, heterogeneity=0.8), family="latent"
    )
    sweep = calibration_sweep(base, seeds=4, bias_values=(0.4,))
    raw = sweep["raw"][-1]["completion_rate"]
    rel = sweep["reliability"][-1]["completion_rate"]
    assert rel > raw


def test_track_record_sweep_recovery_grows_with_history():
    base = CellParams(n_agents=60, n_tasks=48, n_domains=4, heterogeneity=0.8)
    sweep = track_record_sweep(base, seeds=4, windows=(2, 40))
    short, long = sweep[0], sweep[-1]
    # The correction recovers completion at both lengths, and a longer track
    # record (a sharper reliability estimate) recovers more.
    assert short["recovery"] > 0.0
    assert long["recovery"] >= short["recovery"]
    # A longer history also calibrates the retained winners better (lower Brier).
    assert long["reliability_brier"] <= short["reliability_brier"] + 1e-9


def test_safety_ablation_gate_reduces_violations():
    base = CellParams(n_agents=60, n_tasks=48, n_domains=4, heterogeneity=0.8)
    res = safety_ablation(base, seeds=3, adversarial_fraction=0.4, gate_recall=0.9)
    on = sum(res["gate_on_violations"])
    off = sum(res["gate_off_violations"])
    # With an imperfect gate the violation count falls substantially but need not
    # reach zero; without the gate every out-of-scope action executes.
    assert off > 0
    assert on < off
    assert 1.0 - on / off >= 0.667

    # A perfect-recall gate blocks every out-of-scope action.
    perfect = safety_ablation(base, seeds=3, adversarial_fraction=0.4, gate_recall=1.0)
    assert sum(perfect["gate_on_violations"]) == 0


def test_stability_grid_shape_and_monotonicity():
    base = CellParams(n_agents=40, n_tasks=32, n_domains=4, heterogeneity=0.8)
    grid = stability_grid(base, seeds=2, ea_values=(0.1, 0.5, 0.9), t_values=(0.0,))
    assert len(grid) == 3
    unmet = [c["unmet_rate"] for c in grid]
    # A higher barrier should not reduce the unmet rate.
    assert unmet[-1] >= unmet[0] - 1e-9
