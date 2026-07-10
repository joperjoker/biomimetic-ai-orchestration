"""H13: a persistent, accumulating track record makes the allocation self-improve."""

from cta.harness import CellParams, learning_curve
from cta.report import evaluate


def test_reliability_self_improves_while_raw_stays_flat():
    base = CellParams(n_agents=40, n_tasks=32, n_domains=4)
    r = learning_curve(base, seeds=10, rounds=10)
    rel = r["completion"]["reliability"]
    assert len(rel) == 10
    # Reliability starts low (cold record, ranks like raw) and climbs materially as
    # the track record accumulates: the last round clears the first by a wide margin.
    assert rel[-1] > rel[0] + 0.2
    assert r["reliability_lift"] > 0.2
    # Raw has no track-record term in the bid, so it does not learn: roughly flat.
    assert abs(r["raw_lift"]) < 0.1
    assert r["reliability_lift"] > r["raw_lift"] + 0.1


def test_learning_curve_is_deterministic():
    base = CellParams(n_agents=40, n_tasks=32, n_domains=4)
    a = learning_curve(base, seeds=6, rounds=6)
    b = learning_curve(base, seeds=6, rounds=6)
    assert a["completion"] == b["completion"]


def test_h13_verdict_supported():
    base = CellParams(n_agents=40, n_tasks=32, n_domains=4)
    lc = learning_curve(base, seeds=10, rounds=10)
    verdicts = evaluate({}, {}, {}, learning=lc)
    assert verdicts["H13"]["verdict"] == "SUPPORTED"
