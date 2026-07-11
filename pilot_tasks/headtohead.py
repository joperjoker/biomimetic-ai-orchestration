"""Phase 2C: the head-to-head on real agents, as a leave-one-replicate-out replay.

The Phase 3 capability ladder already ran every model (Haiku, Sonnet, Opus) on
every expert task across ~10 replicates, recording each run's stated confidence
and hidden-test outcome (``results/live_pilot/ladder/``). The head-to-head is a
*routing* question over those outcomes: given the same real self-reports and real
pass/fail, what completion and cost does each policy achieve? So it is answerable
from the banked data with **no new subagent spend**, using leave-one-replicate-out
cross-validation so no policy sees the outcome it is scored on.

For each held-out replicate ``r``:

- estimate each model's per-task **reliability** and mean **self-report** from the
  *other* replicates (no foresight), and
- route each task under each policy, then look up the routed model's *actual* pass
  on replicate ``r`` and its cost.

Averaging over the held-out replicates gives per-policy completion (with a
bootstrap CI over folds), cost, and the head-to-head deltas. The ``bare`` condition
is used: it is the model's unaided capability, the clean setting for an
agent-router comparison (the task wrapper is a separate mechanism).

Run: ``python -m pilot_tasks.headtohead`` (writes ``results/headtohead/``).
Because it only reads existing files it is fully deterministic and re-runnable; if
the ladder data is absent it exits with a clear message rather than spending
budget.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from cta.cost import PRICING
from cta.headtohead import POLICIES, _choose, _fresh_fleet
from cta.stats import bootstrap_ci
from cta.viz import bar_chart, save_svg
from cta.wrappers import Model
from pilot_tasks.expert_suite import TASK_NAMES
from pilot_tasks.ladder import LADDER, load

OUT = Path("results/headtohead")
FIGS = Path("results/figures")

MODELS = [Model("haiku", "economy"), Model("sonnet", "standard"), Model("opus", "premium")]
TOKENS_PER_TASK = 4000.0
BARRIER = 0.7
CONDITION = "bare"

_LABEL = {
    "cta_corrected": "CTA (corrected)",
    "naive_self_report": "naive self-report",
    "always_frontier": "always frontier",
    "single_cheapest": "single cheapest",
}


def _blended_rate(tier: str) -> float:
    lo, hi = PRICING[tier]
    return (lo + hi) / 2.0


def _index(records: list[dict]) -> dict[str, dict[str, dict[str, dict]]]:
    """rows -> table[replicate][model][task] = {passed, confidence}."""
    table: dict[str, dict[str, dict[str, dict]]] = {}
    for r in records:
        if r["condition"] != CONDITION or r["task"] not in TASK_NAMES:
            continue
        rep = r["agent"].split("__")[-1]  # the replicate number, shared across models
        table.setdefault(rep, {}).setdefault(r["model"], {})[r["task"]] = {
            "passed": bool(r["passed"]),
            "confidence": float(r["confidence"]),
        }
    return table


def _estimate(train: list[str], table: dict, model: str, task: str) -> tuple[float, float]:
    """Mean reliability and mean self-report for (model, task) over training reps."""
    passes, confs = [], []
    for rep in train:
        cell = table.get(rep, {}).get(model, {}).get(task)
        if cell is not None:
            passes.append(1.0 if cell["passed"] else 0.0)
            confs.append(cell["confidence"])
    rel = statistics.fmean(passes) if passes else 0.6
    conf = statistics.fmean(confs) if confs else 0.9
    return rel, conf


def _complete_replicates(table: dict) -> list[str]:
    """Replicates that hold every model x every task (so a fold is well-formed)."""
    good = []
    for rep, models in table.items():
        if all(task in models.get(m.name, {}) for m in MODELS for task in TASK_NAMES):
            good.append(rep)
    return sorted(good)


def _route_fold(policy: str, train: list[str], table: dict) -> dict[str, str]:
    """Route every task under ``policy`` using only the training replicates."""
    fleet = _fresh_fleet(MODELS, BARRIER, None)
    routed: dict[str, str] = {}
    for task in TASK_NAMES:
        rel_conf = {m.name: _estimate(train, table, m.name, task) for m in MODELS}
        if policy == "cta_corrected":
            fleet.reliability = {m: {task: rel_conf[m][0]} for m in rel_conf}
        bids = {m.name: rel_conf[m.name][1] for m in MODELS}  # real mean self-reports
        routed[task] = _choose(policy, fleet, task, bids)
    return routed


def _cost_usd(model: str) -> float:
    tier = next(m.tier for m in MODELS if m.name == model)
    return (TOKENS_PER_TASK / 1e6) * _blended_rate(tier)


def _run_replay(table: dict) -> dict:
    reps = _complete_replicates(table)
    if len(reps) < 3:
        raise SystemExit(
            f"only {len(reps)} complete ladder replicates; need >=3 for the fold CV"
        )
    per_policy = {}
    for policy in POLICIES:
        fold_completion, fold_cost = [], []
        for held in reps:
            train = [r for r in reps if r != held]
            routed = _route_fold(policy, train, table)
            comp = statistics.fmean(
                1.0 if table[held][routed[t]][t]["passed"] else 0.0 for t in TASK_NAMES
            )
            cost = sum(_cost_usd(routed[t]) for t in TASK_NAMES)
            fold_completion.append(comp)
            fold_cost.append(cost)
        mean, lo, hi = bootstrap_ci(fold_completion)
        per_policy[policy] = {
            "folds": len(reps),
            "completion": round(mean, 4),
            "completion_lo": round(lo, 4),
            "completion_hi": round(hi, 4),
            "cost_usd": round(statistics.fmean(fold_cost), 6),
        }
    cta, naive = per_policy["cta_corrected"], per_policy["naive_self_report"]
    frontier = per_policy["always_frontier"]
    comparison = {
        "completion_gain_vs_naive": round(cta["completion"] - naive["completion"], 4),
        "completion_retained_vs_frontier": round(
            cta["completion"] - frontier["completion"], 4
        ),
        "cost_saving_vs_frontier": round(frontier["cost_usd"] / cta["cost_usd"], 2)
        if cta["cost_usd"] else 0.0,
    }
    return {"condition": CONDITION, "policies": per_policy, "comparison": comparison}


def _figure(result: dict, path: Path) -> None:
    pol = result["policies"]
    cats = [_LABEL[p] for p in POLICIES]
    frontier_cost = pol["always_frontier"]["cost_usd"] or 1.0
    completion = [pol[p]["completion"] for p in POLICIES]
    rel_cost = [round(pol[p]["cost_usd"] / frontier_cost, 4) for p in POLICIES]
    svg = bar_chart(
        cats,
        {"completion": completion, "relative cost": rel_cost},
        title="Head-to-head on real agents: completion vs cost by routing policy",
        ylabel="fraction (cost relative to always-frontier)",
        xlabel="routing policy",
    )
    save_svg(svg, path)


def _write(result: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    _figure(result, OUT / "headtohead.svg")
    _figure(result, FIGS / "headtohead.svg")

    pol, cmp = result["policies"], result["comparison"]
    lines = [
        "# Head-to-head on real agents (leave-one-replicate-out replay)",
        "",
        f"Ladder `{CONDITION}` outcomes, {pol['cta_corrected']['folds']} folds. Reliability",
        "and self-reports are estimated from the training replicates only; each policy",
        "is scored on the held-out replicate it did not see.",
        "",
        "| policy | completion (95% CI) | cost per task-set (USD) |",
        "|--------|---------------------|-------------------------|",
    ]
    for p in POLICIES:
        s = pol[p]
        lines.append(
            f"| {_LABEL[p]} | {s['completion']:.3f} "
            f"[{s['completion_lo']:.3f}, {s['completion_hi']:.3f}] | {s['cost_usd']:.5f} |"
        )
    lines += [
        "",
        f"- Completion gain over naive self-report: **{cmp['completion_gain_vs_naive']:+.3f}**.",
        f"- Completion retained versus always-frontier: "
        f"**{cmp['completion_retained_vs_frontier']:+.3f}**.",
        f"- Cost saving versus always-frontier: **{cmp['cost_saving_vs_frontier']:.2f}x**.",
        "",
    ]
    (OUT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> dict:
    if not Path(LADDER).exists():
        raise SystemExit(f"no ladder data at {LADDER}; run the Phase 3 ladder first")
    table = _index(load())
    result = _run_replay(table)
    _write(result)
    return result


if __name__ == "__main__":
    print(json.dumps(main()["comparison"], indent=2))
