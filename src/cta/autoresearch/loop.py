"""The Auto-Researcher loop: propose, evaluate, keep or revert.

The loop maximises a protected primary metric (mean realised quality) subject to
a guardrail (the unmet-task rate must stay below a ceiling, so quality cannot be
raised by simply stalling the hard tasks). Each decision is logged. Evaluation
averages over seeds, so a change is kept only on a real, reproducible gain, not a
single lucky run. No LLM is required; the proposer is deterministic and seeded.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from cta.autoresearch.search_space import SearchPoint, propose
from cta.harness import CellParams, run_seeds


@dataclass
class Decision:
    step: int
    proposal: dict[str, float]
    objective_before: float
    objective_after: float
    unmet_rate: float
    guardrail_ok: bool
    kept: bool


@dataclass
class LoopResult:
    best: SearchPoint
    best_objective: float
    ledger: list[Decision] = field(default_factory=list)


def evaluate_point(point: SearchPoint, base: CellParams, seeds: int) -> tuple[float, float]:
    """Return (objective, unmet_rate) for a search point, averaged over seeds.

    Objective is the mean realised quality; unmet is the fraction of tasks left
    infeasible or stalled, the guardrail quantity.
    """
    params = CellParams(
        n_agents=base.n_agents,
        n_tasks=base.n_tasks,
        n_domains=base.n_domains,
        heterogeneity=base.heterogeneity,
        activation_energy=point.activation_energy,
        temperature=point.temperature,
    )
    rows = run_seeds("cta", params, seeds)
    quality = sum(r["mean_quality"] for r in rows) / len(rows)
    unmet = sum(r["infeasible_rate"] + r["stall_rate"] for r in rows) / len(rows)
    return quality, unmet


def run_loop(
    base: CellParams,
    seeds: int = 5,
    budget: int = 12,
    seed: int = 0,
    min_gain: float = 0.005,
    max_unmet: float = 0.5,
) -> LoopResult:
    """Run the propose, evaluate, keep-or-revert loop within a fixed budget."""
    rng = random.Random(seed)
    current = SearchPoint(base.activation_energy, base.temperature)
    best_obj, _ = evaluate_point(current, base, seeds)
    result = LoopResult(best=current, best_objective=best_obj)

    for step in range(budget):
        candidate = propose(current, rng)
        obj, unmet = evaluate_point(candidate, base, seeds)
        guardrail_ok = unmet <= max_unmet
        kept = guardrail_ok and obj > result.best_objective + min_gain
        result.ledger.append(
            Decision(
                step=step,
                proposal=candidate.as_dict(),
                objective_before=result.best_objective,
                objective_after=obj,
                unmet_rate=unmet,
                guardrail_ok=guardrail_ok,
                kept=kept,
            )
        )
        if kept:
            current = candidate
            result.best = candidate
            result.best_objective = obj
    return result
