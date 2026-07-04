"""P3.2: the track record demotes a strategic overclaimer over rounds."""

from cta.harness import CellParams, strategic_adversary


def test_reliability_demotes_the_adversary_over_rounds():
    base = CellParams(n_agents=40, n_tasks=32, n_domains=4)
    r = strategic_adversary(base, seeds=10, rounds=8)
    share = r["reliability_share"]
    assert len(share) == 8
    # The adversary wins a real share early (it overclaims and starts clean).
    assert share[0] > 0.1
    # As its record catches up with it, reliability selection demotes it towards
    # zero: the final round's share is well below the first, and near zero.
    assert share[-1] < share[0]
    assert share[-1] < 0.05
    assert r["reliability_decay"] > 0.1
