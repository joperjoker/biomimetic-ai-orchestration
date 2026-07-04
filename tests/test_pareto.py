"""The latency-quality Pareto sweep traces a real, non-dominated frontier."""

from cta.harness import CellParams, pareto_front, pareto_sweep


def test_pareto_front_selects_non_dominated_points():
    points = [
        {"mean_quality": 0.90, "mean_latency": 1.00},  # non-dominated (best quality)
        {"mean_quality": 0.88, "mean_latency": 0.70},  # non-dominated (mid)
        {"mean_quality": 0.87, "mean_latency": 0.66},  # non-dominated (fastest)
        {"mean_quality": 0.80, "mean_latency": 0.90},  # dominated by all above
    ]
    front = pareto_front(points)
    assert points[3] not in front
    assert len(front) == 3


def test_sweep_trades_quality_for_latency():
    base = CellParams(n_agents=60, n_tasks=48, n_domains=5)
    rows = pareto_sweep(base, seeds=6, weights=(0.0, 1.0, 2.0))
    assert [r["latency_weight"] for r in rows] == [0.0, 1.0, 2.0]
    # Ignoring latency (weight 0) gives the highest quality and the highest mean
    # latency; leaning on it lowers both.
    assert rows[0]["mean_quality"] >= rows[-1]["mean_quality"]
    assert rows[0]["mean_latency"] > rows[-1]["mean_latency"]
    # The endpoints are on the frontier (a genuine tradeoff, not one dominating).
    front = pareto_front(rows)
    assert rows[0] in front and rows[-1] in front
