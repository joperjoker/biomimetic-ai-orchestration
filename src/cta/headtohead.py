"""The Paper 2 head-to-head: calibration-robust routing versus the alternatives.

Runs a task stream through four routing policies over one model fleet and reports
completion, cost, and the probe overhead elicitation costs. The solver is
pluggable: a deterministic simulated solver drives the tests and a sanity run
here, and a real subagent solver swaps in for the metered run
(``pilot_tasks/headtohead.py``, Phase 2C).

The four policies isolate the paper's mechanism:

- ``cta_corrected``   -- route to the cheapest model whose *reliability-corrected*
  self-report clears the activation barrier (``wrappers.route`` over a track
  record). The track record is the calibration data a real deployment already has
  from prior runs; it is passed in as a warm start and also accrues online.
- ``naive_self_report`` -- route on the *raw* self-report only, no track-record
  correction. Isolates what the correction buys: it over-trusts a cheap model that
  bids high but is unreliable.
- ``always_frontier`` -- always the most capable model. Full completion, full cost.
- ``single_cheapest`` -- always the cheapest model. Low cost, low completion on the
  tasks a cheap model cannot do.

Pure standard library and deterministic. Prices come from ``cta.cost.PRICING`` via
the fleet's blended rate.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from cta.acp import Bidder, prior_bidder
from cta.stats import bootstrap_ci
from cta.viz import bar_chart, save_svg
from cta.wrappers import Fleet, Model, route

POLICIES = ("cta_corrected", "naive_self_report", "always_frontier", "single_cheapest")
_ELICITING = frozenset({"cta_corrected", "naive_self_report"})  # policies that read bids

TOKENS_PER_TASK = 4000.0  # representative solve size, matching wrappers.cost_saving
PROBE_TOKENS = 500.0  # a confidence probe is a short extra turn per candidate


@dataclass(frozen=True)
class Task:
    """One unit of work: a name (unique) and a task_type (the routing key)."""

    name: str
    task_type: str


# A solver returns whether ``model`` passes ``task``. Deterministic in the sim,
# a real subagent solve live.
Solver = Callable[[str, Task], bool]
# A warm-start track record: reliability[model][task_type] = prior pass rate.
WarmStart = "dict[str, dict[str, float]]"


@dataclass(frozen=True)
class TurnOutcome:
    task: str
    task_type: str
    model: str
    passed: bool
    solve_cost_usd: float
    probe_cost_usd: float
    probe_turns: int


def sim_solver(capability: dict[str, float], difficulty: dict[str, float]) -> Solver:
    """A deterministic solver: ``model`` passes ``task`` iff its capability meets
    the task's difficulty. Capability is keyed by model name, difficulty by task
    name."""

    def _solve(model: str, task: Task) -> bool:
        return capability[model] >= difficulty[task.name]

    return _solve


def _fresh_fleet(models: list[Model], barrier: float, warm: WarmStart | None) -> Fleet:
    fleet = Fleet(models=[Model(m.name, m.tier) for m in models], barrier=barrier)
    if warm:
        fleet.reliability = {m: dict(types) for m, types in warm.items()}
    return fleet


def _choose(policy: str, fleet: Fleet, task_type: str, bids: dict[str, float]) -> str:
    """Pick a model for one turn under the named policy."""
    if policy == "always_frontier":
        return fleet.most_capable().name
    if policy == "single_cheapest":
        return fleet.cheapest().name
    if policy == "naive_self_report":
        # No track-record correction: the cheapest model clearing the barrier on
        # its raw bid, else the highest raw bid.
        eligible = [m.name for m in fleet.models if bids.get(m.name, 0.0) >= fleet.barrier]
        return eligible[0] if eligible else max(bids, key=bids.get)
    # cta_corrected: reliability-corrected routing (the paper's mechanism).
    return route(task_type, bids, fleet).model


def run_policy(
    policy: str,
    tasks: list[Task],
    solver: Solver,
    models: list[Model],
    *,
    barrier: float = 0.7,
    bidder: Bidder | None = None,
    warm_start: WarmStart | None = None,
    probe_turns_per_task: int = 0,
) -> list[TurnOutcome]:
    """Run one policy over the task stream, accumulating a track record online for
    the corrected policy. Returns a per-turn outcome list."""
    bidder = bidder or prior_bidder()
    fleet = _fresh_fleet(models, barrier, warm_start if policy == "cta_corrected" else None)
    rates = {m.name: m.blended_rate() for m in fleet.models}
    outcomes: list[TurnOutcome] = []
    for task in tasks:
        bids = bidder(task.task_type, fleet)
        model = _choose(policy, fleet, task.task_type, bids)
        passed = solver(model, task)
        solve_cost = (TOKENS_PER_TASK / 1e6) * rates[model]
        # Only eliciting policies pay the probe overhead, and only in probe mode
        # (probe_turns_per_task > 0). Each candidate is probed once.
        turns = probe_turns_per_task * len(fleet.models) if policy in _ELICITING else 0
        probe_cost = sum((PROBE_TOKENS / 1e6) * rates[m.name] for m in fleet.models) * (
            probe_turns_per_task if policy in _ELICITING else 0
        )
        if policy == "cta_corrected":
            fleet.record(model, task.task_type, passed)  # H13: learn online too
        outcomes.append(
            TurnOutcome(task.name, task.task_type, model, passed, solve_cost, probe_cost, turns)
        )
    return outcomes


def summarise(outcomes: list[TurnOutcome]) -> dict[str, float]:
    """Aggregate a policy's turns: completion with a bootstrap CI, cost, overhead."""
    passes = [1.0 if o.passed else 0.0 for o in outcomes]
    mean, lo, hi = bootstrap_ci(passes)
    solve = sum(o.solve_cost_usd for o in outcomes)
    probe = sum(o.probe_cost_usd for o in outcomes)
    return {
        "n": len(outcomes),
        "completion": round(mean, 4),
        "completion_lo": round(lo, 4),
        "completion_hi": round(hi, 4),
        "solve_cost_usd": round(solve, 6),
        "probe_cost_usd": round(probe, 6),
        "total_cost_usd": round(solve + probe, 6),
        "probe_turns": sum(o.probe_turns for o in outcomes),
    }


def head_to_head(
    tasks: list[Task],
    solver: Solver,
    models: list[Model],
    *,
    barrier: float = 0.7,
    bidder: Bidder | None = None,
    warm_start: WarmStart | None = None,
    probe_turns_per_task: int = 0,
) -> dict[str, dict]:
    """Run all four policies and report per policy plus the head-to-head deltas."""
    per_policy = {
        p: summarise(
            run_policy(
                p, tasks, solver, models,
                barrier=barrier, bidder=bidder, warm_start=warm_start,
                probe_turns_per_task=probe_turns_per_task,
            )
        )
        for p in POLICIES
    }
    cta = per_policy["cta_corrected"]
    naive = per_policy["naive_self_report"]
    frontier = per_policy["always_frontier"]

    def _mult(a: float, b: float) -> float:
        return round(a / b, 2) if b else 0.0

    comparison = {
        # vs naive: the correction should lift completion at comparable cost.
        "completion_gain_vs_naive": round(cta["completion"] - naive["completion"], 4),
        # vs frontier: match completion at a fraction of the cost.
        "completion_retained_vs_frontier": round(cta["completion"] - frontier["completion"], 4),
        "cost_saving_vs_frontier": _mult(frontier["total_cost_usd"], cta["total_cost_usd"]),
        "probe_overhead_fraction": round(
            cta["probe_cost_usd"] / cta["total_cost_usd"], 4
        ) if cta["total_cost_usd"] else 0.0,
    }
    return {"policies": per_policy, "comparison": comparison}


# --- Reporting: figure and markdown/JSON writers -------------------------------

_LABEL = {
    "cta_corrected": "CTA (corrected)",
    "naive_self_report": "naive self-report",
    "always_frontier": "always frontier",
    "single_cheapest": "single cheapest",
}


def completion_cost_figure(result: dict, path: str | Path) -> None:
    """A grouped bar chart: completion and relative cost per policy.

    Cost is shown as a fraction of the always-frontier cost so both series share a
    0..1 scale and the completion/cost trade-off reads at a glance.
    """
    pol = result["policies"]
    cats = [_LABEL[p] for p in POLICIES]
    frontier_cost = pol["always_frontier"]["total_cost_usd"] or 1.0
    completion = [pol[p]["completion"] for p in POLICIES]
    rel_cost = [round(pol[p]["total_cost_usd"] / frontier_cost, 4) for p in POLICIES]
    svg = bar_chart(
        cats,
        {"completion": completion, "relative cost": rel_cost},
        title="Head-to-head: completion versus cost by routing policy",
        ylabel="fraction (cost relative to always-frontier)",
        xlabel="routing policy",
    )
    save_svg(svg, path)


def write_report(result: dict, out_dir: str | Path) -> dict[str, Path]:
    """Write ``summary.json``, ``RESULTS.md``, and the figure into ``out_dir``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(result, indent=2))
    completion_cost_figure(result, out / "headtohead.svg")

    pol, cmp = result["policies"], result["comparison"]
    lines = [
        "# Head-to-head: calibration-robust routing versus the alternatives",
        "",
        "| policy | completion (95% CI) | total cost (USD) | probe cost (USD) |",
        "|--------|---------------------|------------------|------------------|",
    ]
    for p in POLICIES:
        s = pol[p]
        lines.append(
            f"| {_LABEL[p]} | {s['completion']:.3f} "
            f"[{s['completion_lo']:.3f}, {s['completion_hi']:.3f}] | "
            f"{s['total_cost_usd']:.5f} | {s['probe_cost_usd']:.5f} |"
        )
    lines += [
        "",
        f"- Completion gain over naive self-report: **{cmp['completion_gain_vs_naive']:+.3f}**.",
        f"- Completion retained versus always-frontier: "
        f"**{cmp['completion_retained_vs_frontier']:+.3f}**.",
        f"- Cost saving versus always-frontier: **{cmp['cost_saving_vs_frontier']:.2f}x**.",
        f"- Probe overhead as a fraction of total cost: "
        f"**{cmp['probe_overhead_fraction']:.1%}**.",
        "",
    ]
    (out / "RESULTS.md").write_text("\n".join(lines))
    return {
        "summary": out / "summary.json",
        "results": out / "RESULTS.md",
        "figure": out / "headtohead.svg",
    }
