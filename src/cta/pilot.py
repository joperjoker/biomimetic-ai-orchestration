"""The opt-in live pilot: a swarm of real agents behind a client seam.

Stage 2 swaps the synthetic self-report and outcome for a live agent's, but keeps
every other part of the framework: the same eligibility filter, activation barrier,
reliability-weighted selection, and Rejection Gate. The only thing that changes is
where two numbers come from, so the pilot isolates the one quantity the simulation
cannot supply, a real agent's self-assessed compatibility and its realised outcome.

The seam is the ``PilotClient`` protocol with two methods:

- ``assess(agent, task)`` returns the agent's self-reported compatibility in [0, 1]
  (the calibration under study, E13);
- ``perform(agent, task)`` runs the task and returns the realised quality in [0, 1]
  and whether the action stayed in scope.

``MockClient`` implements both deterministically, so the whole pilot pipeline runs
and is tested without any model calls. ``ClaudeAgentClient`` marks where a live
Claude Code subagent plugs in; it makes no call until implemented and approved, so
the scaffold is ready to run but cannot incur cost by accident.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

from cta.engine import _brier_ece
from cta.quality import is_success, realised_quality
from cta.scoring import (
    EPS,
    Agent,
    GateConfig,
    Task,
    compatibility,
    eligible,
    self_reported_compatibility,
)


class PilotClient(Protocol):
    """The seam between the framework and a live (or mock) agent."""

    def assess(self, agent: Agent, task: Task) -> float:
        """Return the agent's self-reported compatibility with the task, in [0, 1]."""
        ...

    def perform(self, agent: Agent, task: Task) -> tuple[float, bool]:
        """Run the task; return the realised quality in [0, 1] and whether in scope."""
        ...


@dataclass
class MockClient:
    """A deterministic client that reproduces the simulation through the seam.

    ``assess`` returns the true compatibility drifted by the agent's calibration
    bias and noise (E13); ``perform`` draws realised quality from the true fit and
    capability (E12) and an in-scope outcome from ``out_of_scope_prob``. This lets
    the pilot pipeline run and be tested end to end with no model calls.
    """

    seed: int = 0

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def assess(self, agent: Agent, task: Task) -> float:
        true_c = compatibility(agent, task)
        return self_reported_compatibility(
            true_c, agent.calibration_bias, agent.calibration_noise, self._rng
        )

    def perform(self, agent: Agent, task: Task) -> tuple[float, bool]:
        true_c = compatibility(agent, task)
        quality = realised_quality(true_c, agent.capability, self._rng)
        in_scope = self._rng.random() >= agent.out_of_scope_prob
        return quality, in_scope


class ClaudeAgentClient:
    """A live Claude Code subagent behind the same seam (not yet wired).

    Implement ``assess`` by asking the subagent to rate its fit for the task on a
    calibrated 0 to 1 scale, and ``perform`` by running the scoped micro-task in an
    isolated git worktree and returning the required-test pass fraction with a scope
    check. Both are gated behind the ``llm`` extra and an explicit budget approval;
    until then they raise, so the scaffold cannot incur cost by accident.
    """

    def __init__(self, model: str = "claude-sonnet-5", budget_usd: float = 0.0) -> None:
        self.model = model
        self.budget_usd = budget_usd

    def assess(self, agent: Agent, task: Task) -> float:  # pragma: no cover - opt-in
        raise NotImplementedError(
            "Live self-assessment is opt-in. Prompt the subagent for a calibrated "
            "compatibility in [0, 1] and parse it here, behind a budget approval."
        )

    def perform(self, agent: Agent, task: Task) -> tuple[float, bool]:  # pragma: no cover - opt-in
        raise NotImplementedError(
            "Live execution is opt-in. Run the scoped micro-task in an isolated "
            "worktree, return the required-test pass fraction and a scope check."
        )


@dataclass
class PilotOutcome:
    task_id: str
    status: str  # COMPLETED, FAILED, INFEASIBLE, STALLED, DEFLECTED
    winner: str | None
    self_report: float | None
    quality: float | None
    violation: bool


@dataclass
class PilotResult:
    outcomes: list[PilotOutcome]
    track_record: dict[str, tuple[int, int]]  # agent_id -> (successes, attempts) after the run

    def summary(self) -> dict[str, float]:
        n = len(self.outcomes)
        counts: dict[str, int] = {}
        for o in self.outcomes:
            counts[o.status] = counts.get(o.status, 0) + 1
        won = [o for o in self.outcomes if o.self_report is not None and o.quality is not None]
        gap = 0.0
        brier = ece = 0.0
        if won:
            gap = sum(o.self_report for o in won) / len(won) - sum(
                o.quality for o in won
            ) / len(won)
            preds = [float(o.self_report) for o in won]
            succ = [1.0 if o.status == "COMPLETED" else 0.0 for o in won]
            brier, ece = _brier_ece(preds, succ)
        return {
            "tasks": n,
            "completed": counts.get("COMPLETED", 0),
            "completion_rate": counts.get("COMPLETED", 0) / n if n else 0.0,
            "deflection_rate": counts.get("DEFLECTED", 0) / n if n else 0.0,
            "integrity_violations": sum(1 for o in self.outcomes if o.violation),
            "overconfidence_gap": gap,
            "winner_brier": brier,
            "winner_ece": ece,
        }


def run_pilot(
    agents: list[Agent],
    tasks: list[Task],
    client: PilotClient,
    activation_energy: float = 0.20,
    gate: GateConfig | None = None,
    gate_enabled: bool = True,
    selection: str = "reliability",
    rng: random.Random | None = None,
) -> PilotResult:
    """Run the framework over a live (or mock) client, one task at a time.

    Selection is the same as the simulation: eligibility, then the activation
    barrier on the self-report, then the bid, then the gate. With
    ``selection='reliability'`` the bid discounts the self-report by the online
    track record (the correction); with ``'raw'`` it ranks on the self-report
    alone (the naive auction). The reliability estimate is updated online from
    realised outcomes, so the correction accumulates as the pilot proceeds.
    """
    cfg = gate if gate is not None else GateConfig()
    grng = rng if rng is not None else random.Random(0)
    record = {a.agent_id: [a.successes, a.attempts] for a in agents}

    def reliability_live(agent_id: str) -> float:
        s, n = record[agent_id]
        return (s + 1) / (n + 2)

    outcomes: list[PilotOutcome] = []
    for task in tasks:
        elig = [a for a in agents if eligible(a, task)]
        if not elig:
            outcomes.append(PilotOutcome(task.task_id, "INFEASIBLE", None, None, None, False))
            continue
        self_reports = {a.agent_id: client.assess(a, task) for a in elig}
        firing = [a for a in elig if self_reports[a.agent_id] >= activation_energy]
        if not firing:
            outcomes.append(PilotOutcome(task.task_id, "STALLED", None, None, None, False))
            continue

        def _bid(a: Agent, reports: dict[str, float] = self_reports) -> float:
            r = reliability_live(a.agent_id) if selection == "reliability" else 1.0
            return reports[a.agent_id] * r / max(a.latency, EPS)

        winner = max(firing, key=lambda a: (_bid(a), -a.latency, a.agent_id))
        if gate_enabled and reliability_live(winner.agent_id) < cfg.acceptance_threshold:
            outcomes.append(
                PilotOutcome(
                    task.task_id, "DEFLECTED", None, self_reports[winner.agent_id], None, False
                )
            )
            continue
        quality, in_scope = client.perform(winner, task)
        # The gate detects an out-of-scope action with recall < 1 (an imperfect
        # detector), so some slip through, as in the batch engine.
        if not in_scope and gate_enabled and grng.random() < cfg.scope_recall:
            outcomes.append(
                PilotOutcome(
                    task.task_id, "DEFLECTED", None, self_reports[winner.agent_id], None, False
                )
            )
            continue
        succeeded = is_success(quality)
        record[winner.agent_id][1] += 1
        record[winner.agent_id][0] += 1 if succeeded else 0
        outcomes.append(
            PilotOutcome(
                task.task_id,
                "COMPLETED" if succeeded else "FAILED",
                winner.agent_id,
                self_reports[winner.agent_id],
                quality,
                not in_scope,
            )
        )
    return PilotResult(outcomes, {k: (v[0], v[1]) for k, v in record.items()})
