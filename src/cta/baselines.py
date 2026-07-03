"""Centralised baselines: the control conditions.

A single scheduler assigns tasks to agents using the same Binding Energy scores,
so the only difference from CTA is the coordination, not the scoring. Two variants:

- ``greedy``: repeatedly take the highest-scoring eligible pair, one task per agent.
- ``optimal``: the one-to-one assignment maximising total Binding Energy (the
  Hungarian objective). Uses ``scipy.optimize.linear_sum_assignment`` when it is
  installed; otherwise a brute-force optimum for small instances. For large
  instances without scipy it falls back to greedy and says so.

The decentralised pull-based baseline lives in ``engine.run_batch`` with
``condition='pull_based'``.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from cta.quality import is_success, realised_quality
from cta.scoring import Agent, Task, binding_energy, compatibility, eligible

BRUTE_FORCE_LIMIT = 7


@dataclass
class Assignment:
    pairs: list[tuple[str, str]]  # (agent_id, task_id)
    method: str


def _score_matrix(agents: list[Agent], tasks: list[Task]) -> list[list[float]]:
    return [
        [binding_energy(a, t) if eligible(a, t) else 0.0 for t in tasks]
        for a in agents
    ]


def greedy_assignment(agents: list[Agent], tasks: list[Task]) -> Assignment:
    scored = [
        (binding_energy(a, t), a.agent_id, t.task_id)
        for a in agents
        for t in tasks
        if eligible(a, t) and binding_energy(a, t) > 0.0
    ]
    scored.sort(key=lambda x: (-x[0], x[1], x[2]))
    used_agents: set[str] = set()
    used_tasks: set[str] = set()
    pairs: list[tuple[str, str]] = []
    for _, aid, tid in scored:
        if aid in used_agents or tid in used_tasks:
            continue
        used_agents.add(aid)
        used_tasks.add(tid)
        pairs.append((aid, tid))
    return Assignment(pairs, "greedy")


def best_assignment(agents: list[Agent], tasks: list[Task]) -> Assignment:
    """Assign each task to its globally best eligible agent, allowing agent reuse.

    This is the fair full-information reference for CTA's setting, where an agent
    may take more than one task, unlike the one-to-one ``greedy`` and ``optimal``
    assignments. Each task is given the agent that maximises the expected realised
    quality, the true fit times the true capability (E12), which is the quantity
    the quality metric measures. It is therefore a genuine upper bound that CTA
    should approach from below, not a handicapped one-to-one optimum forced to
    spread work across weaker agents.
    """
    pairs: list[tuple[str, str]] = []
    for t in tasks:
        scored = [
            (compatibility(a, t) * a.capability, a.agent_id)
            for a in agents
            if eligible(a, t) and compatibility(a, t) > 0.0
        ]
        if scored:
            scored.sort(key=lambda x: (-x[0], x[1]))
            pairs.append((scored[0][1], t.task_id))
    return Assignment(pairs, "best")


def _brute_force_optimal(agents: list[Agent], tasks: list[Task]) -> Assignment:
    matrix = _score_matrix(agents, tasks)
    n_a, n_t = len(agents), len(tasks)
    best_score = -1.0
    best: list[tuple[int, int]] = []
    # Assign the smaller side over permutations of the larger side.
    if n_a <= n_t:
        for combo in itertools.permutations(range(n_t), n_a):
            score = sum(matrix[i][combo[i]] for i in range(n_a))
            if score > best_score:
                best_score = score
                best = [(i, combo[i]) for i in range(n_a)]
    else:
        for combo in itertools.permutations(range(n_a), n_t):
            score = sum(matrix[combo[j]][j] for j in range(n_t))
            if score > best_score:
                best_score = score
                best = [(combo[j], j) for j in range(n_t)]
    pairs = [
        (agents[i].agent_id, tasks[j].task_id)
        for i, j in best
        if matrix[i][j] > 0.0
    ]
    return Assignment(pairs, "optimal-bruteforce")


def optimal_assignment(agents: list[Agent], tasks: list[Task]) -> Assignment:
    try:
        from scipy.optimize import linear_sum_assignment  # type: ignore
    except ImportError:
        if min(len(agents), len(tasks)) <= BRUTE_FORCE_LIMIT:
            return _brute_force_optimal(agents, tasks)
        result = greedy_assignment(agents, tasks)
        return Assignment(result.pairs, "greedy-fallback")
    matrix = _score_matrix(agents, tasks)
    # Maximise total score by minimising the negative.
    cost = [[-matrix[i][j] for j in range(len(tasks))] for i in range(len(agents))]
    rows, cols = linear_sum_assignment(cost)
    pairs = [
        (agents[i].agent_id, tasks[j].task_id)
        for i, j in zip(rows, cols, strict=False)
        if matrix[i][j] > 0.0
    ]
    return Assignment(pairs, "optimal-hungarian")


def run_central(
    agents: list[Agent],
    tasks: list[Task],
    rng: random.Random,
    method: str = "greedy",
) -> dict[str, float]:
    """Assign centrally, execute the assigned pairs, and summarise."""
    if method == "greedy":
        assignment = greedy_assignment(agents, tasks)
    elif method == "best":
        assignment = best_assignment(agents, tasks)
    else:
        assignment = optimal_assignment(agents, tasks)
    by_id = {a.agent_id: a for a in agents}
    task_by_id = {t.task_id: t for t in tasks}
    qualities: list[float] = []
    completed = 0
    for aid, tid in assignment.pairs:
        agent, task = by_id[aid], task_by_id[tid]
        q = realised_quality(compatibility(agent, task), agent.capability, rng)
        qualities.append(q)
        if is_success(q):
            completed += 1
    n = len(tasks)
    assigned = len(assignment.pairs)
    return {
        "tasks": n,
        "assigned": assigned,
        "completed": completed,
        "infeasible_rate": (n - assigned) / n if n else 0.0,
        "mean_quality": sum(qualities) / len(qualities) if qualities else 0.0,
        # The central scheduler scores all agent-task pairs at one node each round;
        # this is the coordinator work that the decentralised claim distributes.
        "coordinator_work": len(agents) * len(tasks),
        # A single node does all the work, so the peak per-node load equals the
        # total work: N times M. This is the bottleneck the decentralised design
        # avoids by distributing evaluation across agents.
        "total_work": len(agents) * len(tasks),
        "peak_agent_work": len(agents) * len(tasks),
        "peak_store_load": 0,
        "peak_per_node": len(agents) * len(tasks),
        "method": assignment.method,
    }
