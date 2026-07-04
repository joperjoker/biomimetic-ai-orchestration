"""H10: the activation barrier routes subtasks to correct specialists."""

from cta.harness import CellParams, routing_experiment


def test_barrier_guarantees_routing_above_chance():
    base = CellParams(n_agents=48, n_tasks=40)
    rows = routing_experiment(base, seeds=8, observability_levels=(2, 8), n_roles=4)
    assert [r["observability_k"] for r in rows] == [2, 8]
    for r in rows:
        # With the barrier, ill-matched agents never fire, so routing is near
        # perfect and far above the chance floor.
        assert r["barrier_on_accuracy"] > 0.95
        assert r["barrier_on_accuracy"] > r["chance_floor"]
        # Without the barrier, agents fire on tasks they observe regardless of fit,
        # so routing is materially worse, most under tight observability.
        assert r["barrier_off_accuracy"] < r["barrier_on_accuracy"]


def test_barrier_trades_coverage_for_correctness():
    # The barrier wins fewer tasks (it refuses to misroute) than firing on
    # everything; this is the liveness cost annealing later recovers (H5).
    base = CellParams(n_agents=48, n_tasks=40)
    rows = routing_experiment(base, seeds=8, observability_levels=(2,), n_roles=4)
    assert rows[0]["barrier_on_won"] < rows[0]["barrier_off_won"]
