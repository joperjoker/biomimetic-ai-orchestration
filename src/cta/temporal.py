"""A round-based temporal engine for CTA.

The batch engine in ``engine.py`` allocates a whole set of tasks in one pass and
has no time axis, so it cannot measure allocation latency, starvation, throughput,
or the activation-energy annealing of E14. This module adds a discrete, round-based
simulation over the same scoring model, so those quantities become real measured
outputs rather than aspirations.

Model, per round ``t``:

- Free agents (those not busy on an earlier claim) evaluate the open tasks. An
  agent fires on a task when its self-reported compatibility clears the task's
  current barrier, ``c_hat >= Ea_eff`` (E13, E7).
- ``Ea_eff`` anneals downward the longer a task stays open (E14):
  ``Ea_eff = max(Ea_min, Ea(t) - anneal_rate x open_rounds)``. This bounds the
  stall time of a feasible task, since the barrier eventually drops to where an
  eligible agent fires. An infeasible task (no eligible agent at all) is resolved
  immediately and is never annealed.
- Contention is resolved greedily by the bid: each agent wins at most one task per
  round and each task at most one agent. The winner passes the Rejection Gate
  (reliability and scope integrity, E11); a deflected pair is excluded from future
  rounds so the gate does not livelock.
- An admitted agent is busy for a duration derived from its latency, then the task
  completes with a realised quality (E12). Latency to claim, stall rounds, and
  completion time are recorded per task.

Everything is deterministic given the seeded generator and pure standard library.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from cta.quality import is_success, realised_quality
from cta.scoring import (
    EPS,
    Agent,
    GateConfig,
    Task,
    compatibility,
    eligible,
    reliability,
    self_reported_compatibility,
)


@dataclass(frozen=True)
class TemporalConfig:
    base_duration: float = 2.0  # rounds of work scaled by agent latency
    anneal_rate: float = 0.05  # barrier reduction per open round (E14)
    ea_min: float = 0.0
    annealing: bool = True
    max_rounds: int = 300
    selection_mode: str = "reliability"
    observability_k: int | None = None
    gate_enabled: bool = True
    gate: GateConfig = field(default_factory=GateConfig)


@dataclass
class TemporalOutcome:
    task_id: str
    status: str  # COMPLETED, FAILED, INFEASIBLE, UNRESOLVED, and in-flight CLAIMED
    winner: str | None
    quality: float | None
    advertised_at: int
    claimed_at: int | None
    completed_at: int | None
    stall_rounds: int
    violation: bool


@dataclass
class TemporalResult:
    outcomes: list[TemporalOutcome]
    rounds: int
    deflections: int

    def summary(self) -> dict[str, float]:
        n = len(self.outcomes)
        counts: dict[str, int] = {}
        for o in self.outcomes:
            counts[o.status] = counts.get(o.status, 0) + 1
        completed = [o for o in self.outcomes if o.status == "COMPLETED"]
        claimed = [o for o in self.outcomes if o.claimed_at is not None]
        latencies = [o.claimed_at - o.advertised_at for o in claimed]  # type: ignore[operator]
        stalls = [o.stall_rounds for o in self.outcomes]
        unresolved = counts.get("UNRESOLVED", 0) + counts.get("CLAIMED", 0)
        qualities = [o.quality for o in completed if o.quality is not None]
        return {
            "tasks": n,
            "completed": counts.get("COMPLETED", 0),
            "completion_rate": counts.get("COMPLETED", 0) / n if n else 0.0,
            "failed": counts.get("FAILED", 0),
            "infeasible_rate": counts.get("INFEASIBLE", 0) / n if n else 0.0,
            "unmet_rate": (counts.get("INFEASIBLE", 0) + unresolved) / n if n else 0.0,
            "integrity_violations": sum(1 for o in self.outcomes if o.violation),
            "mean_quality": sum(qualities) / len(qualities) if qualities else 0.0,
            "mean_latency": sum(latencies) / len(latencies) if latencies else 0.0,
            "p95_latency": _percentile(latencies, 0.95),
            "max_stall": max(stalls, default=0),
            "throughput": counts.get("COMPLETED", 0) / self.rounds if self.rounds else 0.0,
            "deflections": self.deflections,
            "rounds": self.rounds,
        }


def _percentile(values: list[int], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(math.ceil(q * len(ordered)) - 1))
    return float(ordered[idx])


def _duration(agent: Agent, base_duration: float) -> int:
    return max(1, round(base_duration * agent.latency))


def _bid(mode: str, c_self: float, c_true: float, agent: Agent) -> float:
    lat = max(agent.latency, EPS)
    if mode == "true":
        cap = 0.0 if agent.capability < 0.0 else 1.0 if agent.capability > 1.0 else agent.capability
        return c_true * cap / lat
    if mode == "raw":
        return c_self / lat
    return c_self * reliability(agent) / lat


def run_temporal(
    agents: list[Agent],
    tasks: list[Task],
    rng: random.Random,
    config: TemporalConfig | None = None,
) -> TemporalResult:
    """Simulate the allocation over discrete rounds and return per-task outcomes."""
    cfg = config if config is not None else TemporalConfig()

    m = len(tasks)
    observed: dict[str, set[int]] | None = None
    if cfg.observability_k is not None and cfg.observability_k < m:
        observed = {a.agent_id: set(rng.sample(range(m), cfg.observability_k)) for a in agents}

    # Precompute the true fit and the (fixed) self-report for every eligible pair.
    true_c: dict[tuple[str, str], float] = {}
    self_c: dict[tuple[str, str], float] = {}
    eligible_any: list[bool] = []
    for ti, task in enumerate(tasks):
        any_elig = False
        for a in agents:
            if observed is not None and ti not in observed[a.agent_id]:
                continue
            if not eligible(a, task):
                continue
            any_elig = True
            key = (a.agent_id, task.task_id)
            tc = compatibility(a, task)
            true_c[key] = tc
            self_c[key] = self_reported_compatibility(
                tc, a.calibration_bias, a.calibration_noise, rng
            )
        eligible_any.append(any_elig)

    outcomes = [
        TemporalOutcome(
            task_id=t.task_id,
            status="INFEASIBLE" if not eligible_any[i] else "OPEN",
            winner=None,
            quality=None,
            advertised_at=0,
            claimed_at=None,
            completed_at=None,
            stall_rounds=0,
            violation=False,
        )
        for i, t in enumerate(tasks)
    ]
    by_agent = {a.agent_id: a for a in agents}
    idx_by_task = {t.task_id: i for i, t in enumerate(tasks)}
    busy_until: dict[str, int] = {a.agent_id: 0 for a in agents}
    blacklist: set[tuple[str, str]] = set()
    deflections = 0

    def open_indices() -> list[int]:
        return [i for i, o in enumerate(outcomes) if o.status == "OPEN"]

    t = 0
    while t < cfg.max_rounds:
        # Finalise any in-flight tasks whose worker has finished.
        for o in outcomes:
            if o.status == "CLAIMED" and o.completed_at is not None and o.completed_at <= t:
                q = o.quality if o.quality is not None else 0.0
                o.status = "COMPLETED" if is_success(q) else "FAILED"

        pending = open_indices()
        in_flight = any(o.status == "CLAIMED" for o in outcomes)
        if not pending and not in_flight:
            break

        free = [a for a in agents if busy_until[a.agent_id] <= t]
        # Build the firing candidates across all open tasks for the free agents.
        candidates: list[tuple[float, str, str]] = []
        for i in pending:
            task = tasks[i]
            open_rounds = t - outcomes[i].advertised_at
            ea_eff = task.activation_energy
            if cfg.annealing:
                ea_eff = max(cfg.ea_min, task.activation_energy - cfg.anneal_rate * open_rounds)
            for a in free:
                key = (a.agent_id, task.task_id)
                if key in blacklist or key not in self_c:
                    continue
                if self_c[key] >= ea_eff:
                    bid = _bid(cfg.selection_mode, self_c[key], true_c[key], a)
                    candidates.append((bid, task.task_id, a.agent_id))

        candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
        used_agents: set[str] = set()
        used_tasks: set[str] = set()
        for _, tid, aid in candidates:
            if aid in used_agents or tid in used_tasks:
                continue
            agent = by_agent[aid]
            o = outcomes[idx_by_task[tid]]
            gate_active = cfg.gate_enabled
            # Reliability screen.
            if gate_active and reliability(agent) < cfg.gate.acceptance_threshold:
                blacklist.add((aid, tid))
                deflections += 1
                continue
            # Scope integrity, with the gate detecting an out-of-scope act at recall.
            in_scope = rng.random() >= agent.out_of_scope_prob
            if not in_scope and gate_active and rng.random() < cfg.gate.scope_recall:
                blacklist.add((aid, tid))
                deflections += 1
                continue
            # Admitted: the agent claims the task and works for a duration.
            used_agents.add(aid)
            used_tasks.add(tid)
            dur = _duration(agent, cfg.base_duration)
            busy_until[aid] = t + dur
            o.status = "CLAIMED"
            o.winner = aid
            o.claimed_at = t
            o.completed_at = t + dur
            o.stall_rounds = t - o.advertised_at
            o.violation = not in_scope
            o.quality = realised_quality(true_c[(aid, tid)], agent.capability, rng)

        t += 1

    # Anything still open or in flight at the horizon is unresolved.
    for o in outcomes:
        if o.status in ("OPEN", "CLAIMED"):
            o.stall_rounds = max(o.stall_rounds, t - o.advertised_at)
            o.status = "UNRESOLVED" if o.status == "OPEN" else o.status
            if o.status == "CLAIMED":
                # Started but not finished by the horizon; count as unresolved work.
                o.status = "UNRESOLVED"

    return TemporalResult(outcomes=outcomes, rounds=t, deflections=deflections)
