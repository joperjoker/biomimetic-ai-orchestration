"""Tests for the generators, quality model, simulation engine, and baselines."""

import random

from cta.baselines import greedy_assignment, optimal_assignment, run_central
from cta.engine import _brier_ece, run_batch
from cta.generators import (
    generate_agents,
    generate_tasks,
    with_capability_spread,
    with_injected_adversarial,
    with_miscalibration,
    with_track_record,
)
from cta.quality import is_success, realised_quality
from cta.scoring import Agent, Task, binding_energy, eligible


def test_generators_counts_and_determinism():
    a1 = generate_agents(10, 4, 0.8, random.Random(1))
    a2 = generate_agents(10, 4, 0.8, random.Random(1))
    assert len(a1) == 10
    assert [a.agent_id for a in a1] == [a.agent_id for a in a2]
    assert [a.capability_vector for a in a1] == [a.capability_vector for a in a2]
    tasks = generate_tasks(5, 4, random.Random(2))
    assert len(tasks) == 5


def test_heterogeneity_specialisation():
    # Specialised agents concentrate capability on one domain (max weight high);
    # homogeneous agents spread it (max weight lower on average).
    spec = generate_agents(40, 4, 1.0, random.Random(3))
    homo = generate_agents(40, 4, 0.0, random.Random(3))
    spec_peak = sum(max(a.capability_vector) for a in spec) / len(spec)
    homo_peak = sum(max(a.capability_vector) for a in homo) / len(homo)
    assert spec_peak > homo_peak


def test_quality_deterministic_and_threshold():
    q1 = realised_quality(0.9, 0.9, random.Random(5))
    q2 = realised_quality(0.9, 0.9, random.Random(5))
    assert q1 == q2
    assert is_success(0.8) is True
    assert is_success(0.5) is False


def test_run_batch_cta_allocates_and_is_deterministic():
    agents = generate_agents(30, 4, 0.8, random.Random(7))
    tasks = generate_tasks(20, 4, random.Random(8))
    r1 = run_batch(agents, tasks, random.Random(9), condition="cta").summary()
    r2 = run_batch(agents, tasks, random.Random(9), condition="cta").summary()
    assert r1 == r2
    assert r1["tasks"] == 20
    assert r1["completed"] >= 1


def test_infeasible_when_no_eligible_agent():
    # An agent lacking the required tool is ineligible, so the task is infeasible.
    task = Task("t", required_tools=frozenset({"deploy"}), requirement_vector=(1.0,))
    agent = Agent(agent_id="a", tools=frozenset({"edit"}), capability_vector=(1.0,))
    assert eligible(agent, task) is False
    res = run_batch([agent], [task], random.Random(1), condition="cta")
    assert res.outcomes[0].status == "INFEASIBLE"


def test_pull_based_has_no_stall_or_deflect():
    agents = generate_agents(20, 3, 0.5, random.Random(11))
    tasks = generate_tasks(15, 3, random.Random(12))
    res = run_batch(agents, tasks, random.Random(13), condition="pull_based").summary()
    assert res["stall_rate"] == 0.0
    assert res["deflection_rate"] == 0.0


def test_optimal_at_least_greedy_total_score():
    agents = generate_agents(5, 3, 0.9, random.Random(21))
    tasks = generate_tasks(5, 3, random.Random(22))
    by_a = {a.agent_id: a for a in agents}
    by_t = {t.task_id: t for t in tasks}

    def total(assignment):
        return sum(binding_energy(by_a[aid], by_t[tid]) for aid, tid in assignment.pairs)

    greedy = greedy_assignment(agents, tasks)
    opt = optimal_assignment(agents, tasks)
    assert total(opt) >= total(greedy) - 1e-9


def test_partial_observability_bounds_peak_agent_work():
    agents = generate_agents(80, 4, 0.8, random.Random(41))
    tasks = generate_tasks(60, 4, random.Random(42))
    full = run_batch(agents, tasks, random.Random(43), condition="cta").summary()
    bounded = run_batch(
        agents, tasks, random.Random(43), condition="cta", observability_k=16
    ).summary()
    # Full observability: each agent evaluates every task; bounded: at most k.
    assert full["peak_agent_work"] == 60
    assert bounded["peak_agent_work"] == 16
    # The bounded per-node load is far below the central N*M load.
    assert bounded["peak_per_node"] < len(agents) * len(tasks)


def test_selection_uses_self_report_but_scores_true_fit():
    # Under a wide competence spread and overconfident self-reports, the raw
    # self-report auction completes fewer tasks than the track-record correction,
    # because raw selection is blind to competence while quality depends on it.
    agents = generate_agents(60, 4, 0.8, random.Random(7))
    agents = with_capability_spread(agents, 0.2)
    agents = with_track_record(agents, random.Random(7 + 40_000))
    agents = with_miscalibration(agents, 0.4, 0.05, random.Random(7 + 60_000))
    tasks = generate_tasks(48, 4, random.Random(8), 0.2)
    raw = run_batch(
        agents, tasks, random.Random(9), condition="cta", selection_mode="raw"
    ).summary()
    rel = run_batch(
        agents, tasks, random.Random(9), condition="cta", selection_mode="reliability"
    ).summary()
    assert rel["completion_rate"] > raw["completion_rate"]
    # Winners over-report: their self-report exceeds the quality they deliver.
    assert raw["overconfidence_gap"] > 0.0


def test_gate_prevents_out_of_scope_writes():
    agents = generate_agents(40, 4, 0.8, random.Random(11))
    agents = with_injected_adversarial(agents, 0.5, random.Random(11 + 70_000))
    tasks = generate_tasks(30, 4, random.Random(12), 0.2)
    on = run_batch(
        agents, tasks, random.Random(13), condition="cta", gate_enabled=True
    ).summary()
    off = run_batch(
        agents, tasks, random.Random(13), condition="cta", gate_enabled=False
    ).summary()
    # With the gate on, no out-of-scope write executes; with it off, some do.
    assert on["integrity_violations"] == 0
    assert off["integrity_violations"] > 0


def test_latent_family_is_deterministic_and_distinct():
    import statistics

    from cta.scoring import compatibility

    a1 = generate_agents(20, 4, 0.8, random.Random(1), family="latent")
    a2 = generate_agents(20, 4, 0.8, random.Random(1), family="latent")
    assert [a.capability_vector for a in a1] == [a.capability_vector for a in a2]
    # The latent family has no discrete skill gate, so its compatibility is a
    # smooth continuum rather than the near-binary one-hot matches of the domains
    # family: the mean is higher and there are no exact zeros from missing skills.
    tk = generate_tasks(20, 4, random.Random(2), family="latent")
    dom = generate_agents(20, 4, 0.8, random.Random(1), family="domains")
    dtk = generate_tasks(20, 4, random.Random(2), family="domains")
    latent_c = [compatibility(a, t) for a in a1 for t in tk]
    domain_c = [compatibility(a, t) for a in dom for t in dtk]
    assert statistics.mean(latent_c) > statistics.mean(domain_c)


def test_unknown_family_rejected():
    try:
        generate_agents(3, 4, 0.5, random.Random(1), family="bogus")
    except ValueError:
        return
    raise AssertionError("expected ValueError for an unknown generator family")


def test_brier_ece_calibration():
    # A perfectly calibrated predictor (predicts the outcome) scores zero.
    brier, ece = _brier_ece([1.0, 0.0, 1.0, 0.0], [1.0, 0.0, 1.0, 0.0])
    assert brier == 0.0
    assert ece == 0.0
    # A confidently wrong predictor scores the worst possible Brier of one.
    brier, ece = _brier_ece([1.0, 1.0], [0.0, 0.0])
    assert brier == 1.0
    assert ece == 1.0
    # An empty sample is defined as zero.
    assert _brier_ece([], []) == (0.0, 0.0)


def test_unknown_selection_mode_rejected():
    agents = generate_agents(5, 3, 0.8, random.Random(1))
    tasks = generate_tasks(3, 3, random.Random(2))
    try:
        run_batch(agents, tasks, random.Random(3), selection_mode="bogus")
    except ValueError:
        return
    raise AssertionError("expected ValueError for an unknown selection mode")


def test_run_central_completes_some():
    agents = generate_agents(8, 3, 0.8, random.Random(31))
    tasks = generate_tasks(6, 3, random.Random(32))
    summary = run_central(agents, tasks, random.Random(33), method="greedy")
    assert summary["tasks"] == 6
    assert summary["assigned"] >= 1
