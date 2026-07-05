"""P3.1: the atomic claim holds under real multi-process contention."""

from cta.concurrent import concurrency_sweep, run_concurrent_claim


def test_no_double_claims_across_processes(tmp_path):
    r = run_concurrent_claim(4, 20, tmp_path / "c.db")
    # Every task is claimed exactly once, and the database agrees.
    assert r["double_claims"] == 0
    assert r["unique_claimed"] == r["tasks"] == 20
    assert r["db_claimed"] == 20


def test_invariant_holds_across_worker_counts(tmp_path):
    sweep = concurrency_sweep((1, 2, 4), 15, tmp_path)
    assert [s["workers"] for s in sweep] == [1, 2, 4]
    for s in sweep:
        # No double-claims at any contention level, and all tasks are claimed.
        assert s["double_claims"] == 0
        assert s["unique_claimed"] == 15
        assert s["throughput"] > 0.0
