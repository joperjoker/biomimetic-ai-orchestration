"""The proof-of-concept runs end to end and demonstrates the gate and the cost."""

from examples.poc import run_poc


def test_poc_runs_and_demonstrates_the_mechanism():
    r = run_poc()
    # One allocation decision per task.
    assert len(r["allocation"]) == r["n_tasks"]
    assert all({"task", "winner", "status"} <= set(a) for a in r["allocation"])
    # The scenario completes some work and the gate stops at least one out-of-scope
    # action (half the fleet is adversarial), so the demo is not vacuous.
    assert r["completed"] >= 1
    assert r["prevented_violations"] >= 1
    # The coordinator's per-node bill is far below the central N-times-M bill.
    assert r["central_cost_usd"] > r["decentralised_per_node_usd"] > 0.0
    assert r["savings_multiple"] > 1.0


def test_poc_is_deterministic():
    assert run_poc() == run_poc()
