"""Tests for the H3, H4, and H5 evaluations."""

from cta.harness import CellParams, feasibility_check, gate_ablation, stability_grid


def test_feasibility_labelling_is_correct():
    base = CellParams(n_agents=30, n_tasks=10, n_domains=4, heterogeneity=0.8)
    res = feasibility_check(base, seed=0)
    # Tasks requiring an absent tool are infeasible; unreachable Ea stalls them.
    assert res["infeasible_recall"] == 1.0
    assert res["stalled_recall"] == 1.0


def test_gate_ablation_helps_under_unreliability():
    base = CellParams(n_agents=60, n_tasks=48, n_domains=4, heterogeneity=0.8)
    res = gate_ablation(base, seeds=4, unreliable_fraction=0.5)
    on = sum(res["gate_on_quality"]) / len(res["gate_on_quality"])
    off = sum(res["gate_off_quality"]) / len(res["gate_off_quality"])
    # With half the agents unreliable, the gate should not reduce quality.
    assert on >= off - 1e-9


def test_stability_grid_shape_and_monotonicity():
    base = CellParams(n_agents=40, n_tasks=32, n_domains=4, heterogeneity=0.8)
    grid = stability_grid(base, seeds=2, ea_values=(0.1, 0.5, 0.9), t_values=(0.0,))
    assert len(grid) == 3
    unmet = [c["unmet_rate"] for c in grid]
    # A higher barrier should not reduce the unmet rate.
    assert unmet[-1] >= unmet[0] - 1e-9
