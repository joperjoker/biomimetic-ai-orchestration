"""In-process simulation engine for the decentralised conditions.

This is the fast, deterministic event loop used for the scaling sweeps. It runs a
batch of tasks against a population of agents under a chosen condition and returns
per-task outcomes and a summary. The concurrent-process mode over the store (for
faithful contention) is a separate engine; both share this scoring logic.

Conditions:
- ``cta``: eligibility, then activation on the self-reported compatibility
  (``c_hat >= Ea``), winner by the bid (``selection_mode``), then the Rejection
  Gate. Realised quality uses the true compatibility, so self-assessment
  miscalibration corrupts the allocation without changing the ground truth.
- ``pull_based``: eligibility only, winner by the true-fit bid, no barrier, no
  gate. This isolates the effect of CTA's mechanisms from decentralisation alone.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

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

SELECTION_MODES = ("reliability", "raw", "true", "quality")


@dataclass
class TaskOutcome:
    task_id: str
    status: str  # COMPLETED, FAILED, INFEASIBLE, STALLED, DEFLECTED
    winner: str | None
    quality: float | None
    fired: int  # number of agents that attempted to claim (contention)
    violation: bool = False  # an out-of-scope write that executed (gate absent or off)
    self_report: float | None = None  # the winner's self-reported compatibility (E13)


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
        integrity_violations = sum(1 for o in self.outcomes if o.violation)
        # Overconfidence gap (E13): how far winners' self-reports exceed the
        # realised quality they deliver. Positive means the pool is overconfident.
        won = [o for o in self.outcomes if o.self_report is not None and o.quality is not None]
        if won:
            mean_sr = sum(o.self_report for o in won) / len(won)
            mean_wq = sum(o.quality for o in won) / len(won)
            overconfidence_gap = mean_sr - mean_wq
            # Calibration of the self-report as a success predictor (winners only):
            # the Brier score and the expected calibration error against the binary
            # success outcome. This is the language the auction literature uses.
            preds = [float(o.self_report) for o in won]
            succ = [1.0 if o.status == "COMPLETED" else 0.0 for o in won]
            winner_brier, winner_ece = _brier_ece(preds, succ)
        else:
            overconfidence_gap = 0.0
            winner_brier = 0.0
            winner_ece = 0.0
        return {
            "tasks": n,
            "completed": counts.get("COMPLETED", 0),
            "completion_rate": counts.get("COMPLETED", 0) / n if n else 0.0,
            "failed": counts.get("FAILED", 0),
            "infeasible_rate": counts.get("INFEASIBLE", 0) / n if n else 0.0,
            "stall_rate": counts.get("STALLED", 0) / n if n else 0.0,
            "deflection_rate": counts.get("DEFLECTED", 0) / n if n else 0.0,
            "integrity_violations": integrity_violations,
            "overconfidence_gap": overconfidence_gap,
            "winner_brier": winner_brier,
            "winner_ece": winner_ece,
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


def _brier_ece(preds: list[float], outcomes: list[float], bins: int = 10) -> tuple[float, float]:
    """Brier score and expected calibration error of predictions against outcomes.

    ``preds`` are predicted success probabilities (here the self-reports) and
    ``outcomes`` the binary successes. The Brier score is the mean squared error.
    The ECE bins the predictions and sums the gap between mean prediction and
    accuracy in each bin, weighted by the bin's share. Both are zero for a
    perfectly calibrated predictor and rise with miscalibration.
    """
    m = len(preds)
    if m == 0:
        return 0.0, 0.0
    brier = sum((p - o) ** 2 for p, o in zip(preds, outcomes, strict=False)) / m
    ece = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        # The last bin includes the right edge so a prediction of 1.0 is counted.
        idx = [i for i, p in enumerate(preds) if (lo <= p < hi) or (b == bins - 1 and p == 1.0)]
        if not idx:
            continue
        mean_p = sum(preds[i] for i in idx) / len(idx)
        acc = sum(outcomes[i] for i in idx) / len(idx)
        ece += (len(idx) / m) * abs(mean_p - acc)
    return brier, ece


def reliability_bins(
    preds: list[float], outcomes: list[float], bins: int = 10
) -> list[dict[str, float]]:
    """Per-bin mean prediction, realised accuracy, and count, for a reliability diagram.

    Bins the predictions into equal-width intervals over [0, 1] and, for each
    non-empty bin, reports the mean predicted value and the fraction of successes.
    A perfectly calibrated predictor lies on the diagonal (mean prediction equals
    accuracy); points above the diagonal are underconfident, below are overconfident.
    """
    out: list[dict[str, float]] = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, p in enumerate(preds) if (lo <= p < hi) or (b == bins - 1 and p == 1.0)]
        if not idx:
            continue
        out.append(
            {
                "mean_prediction": sum(preds[i] for i in idx) / len(idx),
                "accuracy": sum(outcomes[i] for i in idx) / len(idx),
                "count": len(idx),
            }
        )
    return out


def _fires_on(delta: float, temperature: float, rng: random.Random) -> bool:
    """Deterministic threshold firing, with an Arrhenius soft threshold for T > 0."""
    if delta >= 0.0:
        return True
    if temperature <= 0.0:
        return False
    return rng.random() < math.exp(delta / temperature)


def _bid(
    mode: str, c_self: float, c_true: float, agent: Agent, latency_weight: float = 1.0
) -> float:
    """The selection score used to rank the firing agents (E6 family).

    Only signals available at allocation time may enter the bid: the agent's
    self-reported compatibility and its observable track record. True capability
    is not observed; the track record ``R`` is its historical proxy.

    - ``raw``: the self-report alone (``c_hat / L``), the naive auction.
    - ``reliability``: the self-report discounted by the track record
      (``c_hat * R / L``), the treatment that adds a competence signal.
    - ``quality``: the same but without the latency term (``c_hat * R``), a
      quality-first variant used to separate the quality cost of cost-aware
      selection (the ``/ L`` in Binding Energy) from the competence-proxy cost.
    - ``true``: the full-information reference (``c * C / L``), the oracle that
      knows both the true fit and the true capability.

    Latency breaks near-ties as in E6, except in ``quality`` mode where it is
    dropped from the bid entirely. ``latency_weight`` is the exponent on the
    latency term (``/ L ** latency_weight``): 1.0 is the deployed cost-aware bid,
    0.0 ignores latency (a quality-first bid), and larger values favour faster
    agents more aggressively. Sweeping it traces the latency-quality frontier.
    """
    lat = max(agent.latency, EPS) ** latency_weight
    if mode == "true":
        cap = 0.0 if agent.capability < 0.0 else 1.0 if agent.capability > 1.0 else agent.capability
        return c_true * cap / lat
    if mode == "raw":
        return c_self / lat
    if mode == "quality":
        return c_self * reliability(agent)
    # reliability
    return c_self * reliability(agent) / lat


def run_batch(
    agents: list[Agent],
    tasks: list[Task],
    rng: random.Random,
    condition: str = "cta",
    temperature: float = 0.0,
    gate: GateConfig | None = None,
    gate_enabled: bool = True,
    observability_k: int | None = None,
    selection_mode: str = "reliability",
    latency_weight: float = 1.0,
    exposure_cap: int | None = None,
) -> BatchResult:
    """Allocate a batch of tasks under a decentralised condition.

    Each evaluated agent computes its true compatibility ``c`` (E3) and a
    self-report ``c_hat`` (E13). Firing and the bid use the self-report; realised
    quality (E12) uses the true compatibility, so self-assessment miscalibration
    corrupts the allocation without changing the ground truth.

    ``selection_mode`` chooses the bid: ``reliability`` (``c_hat * C * R``, the
    default treatment), ``raw`` (``c_hat * C``, no track record), or ``true``
    (``c * C * R``, the oracle that knows its own fit and so also fires on ``c``).

    ``gate_enabled`` toggles the Rejection Gate for the ablation (H4): it deflects
    an unreliable winner and an out-of-scope action. With the gate off an
    out-of-scope action executes and is recorded as an integrity violation.

    ``observability_k`` (A2) bounds how many tasks each agent observes. With it set,
    an agent evaluates at most ``k`` tasks, so per-agent work and the store hotspot
    stay bounded as the population grows. When None, every agent observes every task.
    """
    if condition not in ("cta", "pull_based"):
        raise ValueError(f"unknown condition: {condition}")
    if selection_mode not in SELECTION_MODES:
        raise ValueError(f"unknown selection_mode: {selection_mode}")
    gate_cfg = gate if gate is not None else GateConfig()
    outcomes: list[TaskOutcome] = []
    # Exposure cap (defence in depth): no single agent wins more than this many
    # tasks per batch, so a newly defecting agent's blast radius is bounded even
    # before its track record updates. None keeps the unthrottled behaviour.
    wins: dict[str, int] = {}

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

        # True fit and the agent's self-report for each eligible agent.
        true_c = {a.agent_id: compatibility(a, task) for a in elig}
        self_c = {
            a.agent_id: self_reported_compatibility(
                true_c[a.agent_id], a.calibration_bias, a.calibration_noise, rng
            )
            for a in elig
        }

        if condition == "cta":
            firing = []
            for a in elig:
                c_fire = true_c[a.agent_id] if selection_mode == "true" else self_c[a.agent_id]
                if _fires_on(c_fire - task.activation_energy, temperature, rng):
                    firing.append(a)
        else:  # pull_based: every eligible agent is willing, ranked on true fit
            firing = elig

        if not firing:
            outcomes.append(TaskOutcome(task.task_id, "STALLED", None, None, 0))
            continue

        pool = firing
        if exposure_cap is not None:
            pool = [a for a in firing if wins.get(a.agent_id, 0) < exposure_cap]
            if not pool:
                # Every willing agent is at its exposure cap: defer the task.
                outcomes.append(TaskOutcome(task.task_id, "STALLED", None, None, len(firing)))
                continue

        winner = max(
            pool,
            key=lambda a: (
                _bid(selection_mode, self_c[a.agent_id], true_c[a.agent_id], a, latency_weight),
                -a.latency,
                a.agent_id,
            ),
        )

        gate_active = condition == "cta" and gate_enabled
        if gate_active and reliability(winner) < gate_cfg.acceptance_threshold:
            outcomes.append(TaskOutcome(task.task_id, "DEFLECTED", None, None, len(firing)))
            continue

        # Integrity check: does the winner act within the task scope (E11)?
        in_scope = rng.random() >= winner.out_of_scope_prob
        if not in_scope and gate_active:
            # The gate detects the out-of-scope action with recall < 1. When it
            # catches it the write is prevented; when it misses, the action
            # executes and is recorded as a violation that slipped past the gate.
            if rng.random() < gate_cfg.scope_recall:
                outcomes.append(TaskOutcome(task.task_id, "DEFLECTED", None, None, len(firing)))
                continue

        q = realised_quality(true_c[winner.agent_id], winner.capability, rng)
        status = "COMPLETED" if is_success(q) else "FAILED"
        wins[winner.agent_id] = wins.get(winner.agent_id, 0) + 1
        outcomes.append(
            TaskOutcome(
                task.task_id,
                status,
                winner.agent_id,
                q,
                len(firing),
                violation=not in_scope,
                self_report=self_c[winner.agent_id],
            )
        )

    return BatchResult(outcomes, total_work=total_work, peak_agent_work=per_agent_work)
