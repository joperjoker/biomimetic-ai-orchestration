"""The biomimicry ablation isolates each mechanism honestly."""

from cta.harness import ABLATION_ARMS, CellParams, biomimicry_ablation
from cta.report import ablation_attribution


def _run():
    base = CellParams(n_agents=40, n_tasks=32, n_domains=4)
    return biomimicry_ablation(base, seeds=8)


def test_ablation_has_all_four_arms():
    ab = _run()
    assert set(ab) == set(ABLATION_ARMS)
    for arm in ab.values():
        assert len(arm["violation_values"]) == 8
        assert len(arm["quality_values"]) == 8


def test_removing_the_gate_increases_violations():
    ab = _run()
    # The integrity gate is the load-bearing safety mechanism: without it, more
    # out-of-scope actions execute.
    assert ab["minus_gate"]["integrity_violations"] > ab["full"]["integrity_violations"]
    analysis = ablation_attribution(ab)
    assert analysis["integrity_gate"]["contributes"] is True
    assert analysis["integrity_gate"]["without_mechanism"] > analysis["integrity_gate"][
        "with_mechanism"
    ]


def test_attribution_reports_barrier_quality_effect_honestly():
    ab = _run()
    analysis = ablation_attribution(ab)
    # The barrier is quality-neutral in the batch regime; the attribution records
    # the (near-zero) effect and does not overclaim a quality contribution.
    assert "activation_barrier" in analysis
    assert abs(float(analysis["activation_barrier"]["effect"])) < 0.05
