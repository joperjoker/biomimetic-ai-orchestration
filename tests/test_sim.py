"""Tests for the generators, quality model, simulation engine, and baselines."""

import random

from cta.baselines import greedy_assignment, optimal_assignment, run_central
from cta.engine import run_batch
from cta.generators import generate_agents, generate_tasks
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


def test_run_central_completes_some():
    agents = generate_agents(8, 3, 0.8, random.Random(31))
    tasks = generate_tasks(6, 3, random.Random(32))
    summary = run_central(agents, tasks, random.Random(33), method="greedy")
    assert summary["tasks"] == 6
    assert summary["assigned"] >= 1
