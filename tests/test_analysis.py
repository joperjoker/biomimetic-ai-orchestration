"""Tests for the statistics utilities and the experiment harness."""

from cta.harness import CellParams, Protocol, aggregate, run_cell, run_seeds, scaling_sweep
from cta.stats import cliffs_delta, holm_bonferroni, mann_whitney_u, mean_ci


def test_mean_ci_basic():
    mean, lo, hi = mean_ci([1.0, 1.0, 1.0])
    assert mean == 1.0 and lo == 1.0 and hi == 1.0
    mean, lo, hi = mean_ci([1.0, 2.0, 3.0, 4.0])
    assert lo < mean < hi


def test_mann_whitney_separates_distributions():
    low = [0.0, 0.1, 0.2, 0.1, 0.05]
    high = [0.9, 0.95, 1.0, 0.85, 0.9]
    _, p = mann_whitney_u(low, high)
    assert p < 0.05
    _, p_same = mann_whitney_u(low, low)
    assert p_same > 0.05


def test_cliffs_delta_sign():
    assert cliffs_delta([3, 4, 5], [0, 1, 2]) == 1.0
    assert cliffs_delta([0, 1, 2], [3, 4, 5]) == -1.0
    assert abs(cliffs_delta([1, 2, 3], [1, 2, 3])) < 1e-9


def test_holm_bonferroni_orders_and_rejects():
    result = holm_bonferroni([0.001, 0.04, 0.5])
    assert result[0][1] is True   # smallest p is rejected
    assert result[2][1] is False  # largest p is not
    # Adjusted p-values are non-decreasing in the original p order here.
    assert result[0][0] <= result[1][0] <= result[2][0]


def test_run_cell_deterministic():
    params = CellParams(n_agents=40, n_tasks=30, n_domains=4, heterogeneity=0.8)
    a = run_cell("cta", params, seed=3)
    b = run_cell("cta", params, seed=3)
    assert a == b
    assert a["condition"] == "cta"


def test_run_seeds_and_aggregate():
    params = CellParams(n_agents=30, n_tasks=20, n_domains=3, heterogeneity=0.7)
    rows = run_seeds("cta", params, seeds=5)
    assert len(rows) == 5
    agg = aggregate(rows, "mean_quality")
    assert agg["n"] == 5
    assert 0.0 <= agg["mean"] <= 1.0
    assert agg["ci_low"] <= agg["mean"] <= agg["ci_high"]


def test_scaling_sweep_small():
    proto = Protocol(
        seeds=2,
        base=CellParams(n_agents=20, n_tasks=16, n_domains=3),
        scaling_n=(20, 40),
    )
    out = scaling_sweep(("cta", "pull_based"), proto, metric="coordinator_work")
    assert set(out.keys()) == {"cta", "pull_based"}
    assert [p["n_agents"] for p in out["cta"]] == [20, 40]


def test_scaling_sweep_central_load_matches_full_run():
    # The central load-only fast path in the sweep must agree with the analytic
    # N times M, so the scaling figure is unaffected by the optimisation.
    proto = Protocol(
        seeds=1,
        base=CellParams(n_agents=20, n_tasks=16, n_domains=3),
        scaling_n=(20, 40),
    )
    out = scaling_sweep(("central_best",), proto, metric="peak_per_node")
    tasks_at = {20: max(1, int(20 * 16 / 20)), 40: max(1, int(40 * 16 / 20))}
    for pt in out["central_best"]:
        assert pt["mean"] == pt["n_agents"] * tasks_at[pt["n_agents"]]
