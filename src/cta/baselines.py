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
from cta.scoring import (
    Agent,
    Task,
    binding_energy,
    compatibility,
    eligible,
    reliability,
    self_reported_compatibility,
)

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


def coordinator_cost(agents: list[Agent], tasks: list[Task]) -> dict[str, float]:
    """The analytic coordinator load fields: N times M pair scores at one node.

    These fields do not depend on which assignment the scheduler picks, so a
    scaling sweep that only needs the load curve can take this fast path and
    skip computing the assignment entirely.
    """
    nm = len(agents) * len(tasks)
    return {
        "coordinator_work": nm,
        "total_work": nm,
        "peak_agent_work": nm,
        "peak_store_load": 0,
        "peak_per_node": nm,
    }


def run_central(
    agents: list[Agent],
    tasks: list[Task],
    rng: random.Random,
    method: str = "greedy",
    quality: bool = True,
) -> dict[str, float]:
    """Assign centrally, execute the assigned pairs, and summarise.

    With ``quality=False`` only the analytic load fields are real; the quality
    fields are zeroed and the assignment is never computed. Use it when a sweep
    reads nothing but the load curve.
    """
    if not quality:
        return {
            "tasks": len(tasks),
            "assigned": 0,
            "completed": 0,
            "infeasible_rate": 0.0,
            "mean_quality": 0.0,
            **coordinator_cost(agents, tasks),
            "method": f"{method}-load-only",
        }
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
        # A single node scores all N times M pairs, so the peak per-node load
        # equals the total work. This is the bottleneck the decentralised
        # design avoids by distributing evaluation across agents.
        **coordinator_cost(agents, tasks),
        "method": assignment.method,
    }


def _stale_reliability_table(
    agents: list[Agent], staleness: float, rng: random.Random
) -> dict[str, float]:
    """Per-agent reliability estimates degraded by ``staleness`` in [0, 1].

    A coordinator's reliability table is synchronised in batches, so it lags. We
    model the lag as a blend between each agent's current reliability (staleness
    0) and an out-of-date value drawn from the prior (staleness 1). Blending
    toward an independent per-agent draw, rather than a shared constant,
    progressively scrambles the competence ranking, which is what a stale table
    actually costs: not a uniform shrink but a loss of who-is-good ordering. Drawn
    once per agent so the estimate is a property of the agent, not of the pair.
    """
    s = 0.0 if staleness < 0.0 else 1.0 if staleness > 1.0 else staleness
    return {a.agent_id: (1.0 - s) * reliability(a) + s * rng.random() for a in agents}


def bounded_assignment(
    agents: list[Agent],
    tasks: list[Task],
    rng: random.Random,
    staleness: float,
    noise: float,
) -> Assignment:
    """Assign each task to the agent that looks best from what a coordinator sees.

    A real central scheduler does not observe true fit or true competence. It
    observes each agent's self-reported compatibility (miscalibrated by the
    agent's own bias and noise, E13, plus ``noise`` of its own observation error)
    and a possibly stale reliability estimate that is its only window onto
    competence. It ranks by the product of the two. Agent reuse is allowed,
    mirroring ``best_assignment`` so the only difference from the full-information
    reference is the *information*, not the matching rule. With ``staleness`` and
    ``noise`` zero and a well-calibrated, uniform fleet the reliability term is a
    common factor, so each task goes to its most compatible eligible agent.
    """
    stale_r = _stale_reliability_table(agents, staleness, rng)
    pairs: list[tuple[str, str]] = []
    for t in tasks:
        best_score = -1.0
        best_id: str | None = None
        for a in agents:
            if not eligible(a, t):
                continue
            true_c = compatibility(a, t)
            if true_c <= 0.0:
                continue
            c_hat = self_reported_compatibility(
                true_c, a.calibration_bias, a.calibration_noise + noise, rng
            )
            perceived = c_hat * stale_r[a.agent_id]
            if perceived > best_score or (perceived == best_score and (
                best_id is None or a.agent_id < best_id
            )):
                best_score = perceived
                best_id = a.agent_id
        if best_id is not None:
            pairs.append((best_id, t.task_id))
    return Assignment(pairs, "bounded")


def run_central_bounded(
    agents: list[Agent],
    tasks: list[Task],
    rng: random.Random,
    staleness: float = 0.0,
    noise: float = 0.0,
) -> dict[str, float]:
    """Central scheduling under bounded information, then execute and summarise.

    This is the honest opponent for CTA: it has the coordinator's ``N`` times
    ``M`` load but only the self-reports and a stale track record to allocate on,
    so unlike the full-information ``best`` reference it is a target CTA's local
    reliability correction can match or beat. Realised quality still uses the true
    compatibility, so the ground truth is identical across all conditions.
    """
    assignment = bounded_assignment(agents, tasks, rng, staleness, noise)
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
        **coordinator_cost(agents, tasks),
        "method": assignment.method,
        "staleness": staleness,
        "report_noise": noise,
    }
