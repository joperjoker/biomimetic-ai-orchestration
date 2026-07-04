"""The coordination cost model scales as the analytics say."""

from cta.cost import (
    PRICING,
    central_cost_usd,
    cost_curve,
    decentralised_cost_usd,
    eval_cost_usd,
    savings_at,
)


def test_eval_cost_matches_pricing():
    in_rate, out_rate = PRICING["standard"]
    expected = (500 * in_rate + 20 * out_rate) / 1_000_000.0
    assert abs(eval_cost_usd("standard") - expected) < 1e-12


def test_central_is_quadratic_and_decentralised_per_node_is_flat():
    # Doubling N (with M proportional to N) roughly quadruples the central bill,
    # while the busiest decentralised node is unchanged.
    c1 = central_cost_usd(1000, 800)
    c2 = central_cost_usd(2000, 1600)
    assert abs(c2 / c1 - 4.0) < 1e-6
    d1 = decentralised_cost_usd(1000, 800, observability_k=32)["per_node_usd"]
    d2 = decentralised_cost_usd(2000, 1600, observability_k=32)["per_node_usd"]
    assert d1 == d2  # bounded by k, independent of N


def test_cost_curve_and_savings_grow_with_scale():
    curve = cost_curve([100, 1000, 10000], task_ratio=0.8, observability_k=32)
    assert [p["n_agents"] for p in curve] == [100, 1000, 10000]
    # The savings multiple of decentralised over central grows with N.
    small = savings_at(100, task_ratio=0.8, observability_k=32)["savings_multiple"]
    big = savings_at(10000, task_ratio=0.8, observability_k=32)["savings_multiple"]
    assert big > small
