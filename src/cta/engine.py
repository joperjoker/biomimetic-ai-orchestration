"""In-process simulation engine for the decentralised conditions.

This is the fast, deterministic event loop used for the scaling sweeps. It runs a
batch of tasks against a population of agents under a chosen condition and returns
per-task outcomes and a summary. The concurrent-process mode over the store (for
faithful contention) is a separate engine; both share this scoring logic.

Conditions:
- ``cta``: eligibility, then activation (``c >= Ea``), winner by Binding Energy,
  then the Rejection Gate.
- ``pull_based``: eligibility only, winner by Binding Energy, no barrier, no gate.
  This isolates the effect of CTA's mechanisms from decentralisation alone.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from cta.quality import is_success, realised_quality
from cta.scoring import (
    Agent,
    GateConfig,
    Task,
    binding_energy,
    compatibility,
    eligible,
    p_fire,
    reliability,
)


@dataclass
class TaskOutcome:
    task_id: str
    status: str  # COMPLETED, FAILED, INFEASIBLE, STALLED, DEFLECTED
    winner: str | None
    quality: float | None
    fired: int  # number of agents that attempted to claim (contention)


@dataclass
class BatchResult:
    outcomes: list[TaskOutcome]
    total_work: int = 0  # total eligibility and compatibility evaluations
    peak_agent_work: int = 0  # the most evaluations any single agent performed

    def summary(self) -> dict[str, float]:
        n = len(self.outcomes)
        counts: dict[str, int] = {}
        for o in self.outcomes:
            counts[o.status] = counts.get(o.status, 0) + 1
        completed = [o for o in self.outcomes if o.status == "COMPLETED"]
        qualities = [o.quality for o in completed if o.quality is not None]
        claim_attempts = sum(o.fired for o in self.outcomes)
        successful_claims = sum(1 for o in self.outcomes if o.winner is not None)
        peak_store_load = max((o.fired for o in self.outcomes), default=0)
        return {
            "tasks": n,
            "completed": counts.get("COMPLETED", 0),
            "failed": counts.get("FAILED", 0),
            "infeasible_rate": counts.get("INFEASIBLE", 0) / n if n else 0.0,
            "stall_rate": counts.get("STALLED", 0) / n if n else 0.0,
            "deflection_rate": counts.get("DEFLECTED", 0) / n if n else 0.0,
            "mean_quality": sum(qualities) / len(qualities) if qualities else 0.0,
            "coordinator_work": claim_attempts,
            "contention": claim_attempts / successful_claims if successful_claims else 0.0,
            # A1: separate the total work from the peak load on any single node.
            # The bottleneck claim is about the peak per-node load, not the total.
            "total_work": self.total_work,
            "peak_agent_work": self.peak_agent_work,
            "peak_store_load": peak_store_load,
            "peak_per_node": max(self.peak_agent_work, peak_store_load),
        }


def _fires(agent: Agent, task: Task, temperature: float, rng: random.Random) -> bool:
    p = p_fire(agent, task, temperature)
    if p >= 1.0:
        return True
    if p <= 0.0:
        return False
    return rng.random() < p


def run_batch(
    agents: list[Agent],
    tasks: list[Task],
    rng: random.Random,
    condition: str = "cta",
    temperature: float = 0.0,
    gate: GateConfig | None = None,
    gate_enabled: bool = True,
    observability_k: int | None = None,
) -> BatchResult:
    """Allocate a batch of tasks under a decentralised condition.

    ``gate_enabled`` toggles the Rejection Gate for the ablation (H4). When it is
    False the winner executes regardless of reliability.

    ``observability_k`` (A2) bounds how many tasks each agent observes. With it set,
    an agent evaluates at most ``k`` tasks, so per-agent work and the store hotspot
    stay bounded as the population grows. When None, every agent observes every task.
    """
    if condition not in ("cta", "pull_based"):
        raise ValueError(f"unknown condition: {condition}")
    gate_cfg = gate if gate is not None else GateConfig()
    outcomes: list[TaskOutcome] = []

    m = len(tasks)
    observed: dict[str, set[int]] | None = None
    if observability_k is not None and observability_k < m:
        observed = {a.agent_id: set(rng.sample(range(m), observability_k)) for a in agents}
        per_agent_work = observability_k
    else:
        per_agent_work = m
    total_work = len(agents) * per_agent_work

    for ti, task in enumerate(tasks):
        if observed is None:
            elig = [a for a in agents if eligible(a, task)]
        else:
            elig = [a for a in agents if ti in observed[a.agent_id] and eligible(a, task)]
        if not elig:
            outcomes.append(TaskOutcome(task.task_id, "INFEASIBLE", None, None, 0))
            continue

        if condition == "cta":
            firing = [a for a in elig if _fires(a, task, temperature, rng)]
        else:  # pull_based: every eligible agent is willing
            firing = elig

        if not firing:
            outcomes.append(TaskOutcome(task.task_id, "STALLED", None, None, 0))
            continue

        winner = max(
            firing,
            key=lambda a: (binding_energy(a, task), -a.latency, a.agent_id),
        )

        gate_active = condition == "cta" and gate_enabled
        if gate_active and reliability(winner) < gate_cfg.acceptance_threshold:
            outcomes.append(TaskOutcome(task.task_id, "DEFLECTED", None, None, len(firing)))
            continue

        q = realised_quality(compatibility(winner, task), winner.capability, rng)
        status = "COMPLETED" if is_success(q) else "FAILED"
        outcomes.append(TaskOutcome(task.task_id, status, winner.agent_id, q, len(firing)))

    return BatchResult(outcomes, total_work=total_work, peak_agent_work=per_agent_work)
