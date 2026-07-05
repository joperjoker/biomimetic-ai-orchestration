"""Capability ladder x wrapper ablation over the expert tier.

Three model families spanning least to most capable (Haiku 4.5, Sonnet 5, Opus
4.8) each solve the eight expert tasks under two conditions:

- ``bare``: the unwrapped prompt (signature and one line).
- ``wrapped``: the CTA **task wrapper** (full envelope with acceptance criteria,
  named edge cases, and a self-check contract).

Submissions live in ``results/live_pilot/ladder/`` named
``{model}__{condition}__{k}.txt``. Real per-run telemetry (tokens, wall-clock)
is recorded alongside in ``telemetry.json`` keyed by that stem.

The analysis reports, per model and condition: fidelity (mean pass fraction),
completion (fraction of tasks fully passed), calibration (Brier, ECE), and the
measured cost and speed. It then evaluates the two wrappers:

- **Task wrapper**: the completion and fidelity lift from ``bare`` to ``wrapped``,
  largest where the model is weakest.
- **Agent wrapper**: CTA Binding-Energy routing. Each task is routed to the
  cheapest model whose reliability-corrected self-report ``c * R`` clears the
  activation barrier; we report the completion retained against always using the
  most capable model, and the token and dollar cost and latency saved.
"""

from __future__ import annotations

import json
import re
import signal
import statistics
from pathlib import Path

from cta.cost import PRICING
from cta.engine import _brier_ece
from cta.viz import bar_chart, line_chart, save_svg
from pilot_tasks.expert_suite import TASK_NAMES, score

LADDER = Path("results/live_pilot/ladder")
FIGS = Path("results/figures")

# Least to most capable. Each maps to a representative price tier from cta.cost.
MODELS = ["haiku", "sonnet", "opus"]
TIER = {"haiku": "economy", "sonnet": "standard", "opus": "premium"}
CONDITIONS = ["bare", "wrapped"]
BARRIER = 0.7  # activation barrier Ea for routing


def _blended_rate(tier: str) -> float:
    """Representative USD per million tokens (mean of input and output rates)."""
    lo, hi = PRICING[tier]
    return (lo + hi) / 2.0


_BLOCK = re.compile(
    r"###\s*TASK:\s*(?P<name>\w+).*?CONFIDENCE:\s*(?P<conf>[0-9.]+).*?```(?:python)?\s*(?P<code>.*?)```",
    re.DOTALL | re.IGNORECASE,
)


class _Timeout(Exception):
    pass


def _run(name: str, code: str, timeout_s: int = 5) -> float:
    """Execute a submitted solution and score it, guarding against a hang."""
    ns: dict = {}

    def _handler(signum, frame):
        raise _Timeout()

    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout_s)
    try:
        exec(code, ns)  # noqa: S102 - our own subagents' toy solutions
        func = ns.get(name)
        if not callable(func):
            return 0.0
        return score(name, func)
    except Exception:
        return 0.0
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def load(path: str | Path = LADDER) -> list[dict]:
    """Parse every ladder submission into (model, condition, agent, task, ...) rows."""
    path = Path(path)
    records: list[dict] = []
    for f in sorted(path.glob("*.txt")):
        parts = f.stem.split("__")
        if len(parts) != 3:
            continue
        model, condition, agent = parts
        text = f.read_text(encoding="utf-8")
        for m in _BLOCK.finditer(text):
            name = m.group("name").strip()
            if name not in TASK_NAMES:
                continue
            frac = _run(name, m.group("code"))
            records.append(
                {
                    "model": model,
                    "condition": condition,
                    "agent": f.stem,
                    "task": name,
                    "confidence": float(m.group("conf")),
                    "pass_fraction": frac,
                    "passed": frac >= 1.0,
                }
            )
    return records


def _telemetry(path: str | Path = LADDER) -> dict:
    f = Path(path) / "telemetry.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _cell(records: list[dict], model: str, condition: str) -> dict:
    rows = [r for r in records if r["model"] == model and r["condition"] == condition]
    if not rows:
        return {}
    conf = [r["confidence"] for r in rows]
    succ = [1.0 if r["passed"] else 0.0 for r in rows]
    frac = [r["pass_fraction"] for r in rows]
    brier, ece = _brier_ece(conf, succ)
    return {
        "attempts": len(rows),
        "fidelity": statistics.mean(frac),
        "completion": statistics.mean(succ),
        "mean_confidence": statistics.mean(conf),
        "overconfidence_gap": statistics.mean(conf) - statistics.mean(succ),
        "brier": brier,
        "ece": ece,
    }


def _task_stats(records: list[dict], condition: str) -> dict:
    """Per (model, task): mean confidence, realised pass, in the given condition."""
    out: dict = {}
    for model in MODELS:
        out[model] = {}
        for task in TASK_NAMES:
            rows = [
                r for r in records
                if r["model"] == model and r["condition"] == condition and r["task"] == task
            ]
            if rows:
                out[model][task] = {
                    "confidence": statistics.mean(r["confidence"] for r in rows),
                    "realised": statistics.mean(r["pass_fraction"] for r in rows),
                    "passed": statistics.mean(1.0 if r["passed"] else 0.0 for r in rows),
                }
    return out


def _route(records: list[dict], tele: dict, condition: str = "wrapped") -> dict:
    """CTA Binding-Energy routing across the ladder against always-most-capable.

    Reliability R is each model's track record: its mean realised pass over the
    tier (leave-one-task-out so a task never reads its own outcome). The bid is
    the model's stated confidence on the task; the corrected bid is ``c * R``.
    Each task goes to the cheapest model whose corrected bid clears the barrier,
    else to the model with the highest corrected bid.
    """
    stats = _task_stats(records, condition)
    if not all(stats[m] for m in MODELS):
        return {}

    # Per-model mean cost (USD) and latency (s) per task, from real telemetry.
    per_task_cost, per_task_latency = {}, {}
    for model in MODELS:
        runs = [
            v for k, v in tele.items()
            if k.startswith(f"{model}__{condition}__")
        ]
        if runs:
            n = len(TASK_NAMES)
            toks = statistics.mean(v["tokens"] for v in runs)
            per_task_cost[model] = (toks / n) / 1e6 * _blended_rate(TIER[model])
            per_task_latency[model] = statistics.mean(v["duration_ms"] for v in runs) / 1000.0 / n

    top = MODELS[-1]  # most capable
    routed_completion, routed_cost, routed_latency, choices = [], [], [], {}
    for task in TASK_NAMES:
        # leave-one-out reliability per model over the other tasks
        reliab = {}
        for model in MODELS:
            others = [stats[model][t]["realised"] for t in TASK_NAMES if t != task]
            reliab[model] = statistics.mean(others) if others else 0.0
        corrected = {m: stats[m][task]["confidence"] * reliab[m] for m in MODELS}
        eligible = [m for m in MODELS if corrected[m] >= BARRIER]
        if eligible:
            choice = min(eligible, key=lambda m: per_task_cost.get(m, float("inf")))
        else:
            choice = max(MODELS, key=lambda m: corrected[m])
        choices[task] = choice
        routed_completion.append(stats[choice][task]["passed"])
        routed_cost.append(per_task_cost.get(choice, 0.0))
        routed_latency.append(per_task_latency.get(choice, 0.0))

    top_completion = statistics.mean(stats[top][t]["passed"] for t in TASK_NAMES)
    top_cost = sum(per_task_cost.get(top, 0.0) for _ in TASK_NAMES)
    top_latency = sum(per_task_latency.get(top, 0.0) for _ in TASK_NAMES)
    r_cost, r_lat = sum(routed_cost), sum(routed_latency)
    return {
        "condition": condition,
        "barrier": BARRIER,
        "choices": choices,
        "routed_completion": statistics.mean(routed_completion),
        "always_top_completion": top_completion,
        "top_model": top,
        "routed_cost_usd": r_cost,
        "always_top_cost_usd": top_cost,
        "cost_saving_multiple": round(top_cost / r_cost, 2) if r_cost else 0.0,
        "routed_latency_s": r_lat,
        "always_top_latency_s": top_latency,
        "latency_saving_multiple": round(top_latency / r_lat, 2) if r_lat else 0.0,
        "per_task_cost_usd": per_task_cost,
        "per_task_latency_s": per_task_latency,
    }


def analyse(path: str | Path = LADDER) -> dict:
    records = load(path)
    tele = _telemetry(path)
    cells = {
        model: {cond: _cell(records, model, cond) for cond in CONDITIONS}
        for model in MODELS
    }
    # task-wrapper lift per model (wrapped minus bare)
    lift = {}
    for model in MODELS:
        b, w = cells[model].get("bare"), cells[model].get("wrapped")
        if b and w:
            lift[model] = {
                "completion_lift": w["completion"] - b["completion"],
                "fidelity_lift": w["fidelity"] - b["fidelity"],
                "ece_change": w["ece"] - b["ece"],
            }
    # per-run telemetry rolled up by model x condition
    tele_cells: dict = {}
    for model in MODELS:
        for cond in CONDITIONS:
            runs = [v for k, v in tele.items() if k.startswith(f"{model}__{cond}__")]
            if runs:
                tele_cells.setdefault(model, {})[cond] = {
                    "mean_tokens": statistics.mean(v["tokens"] for v in runs),
                    "mean_duration_s": statistics.mean(v["duration_ms"] for v in runs) / 1000.0,
                    "runs": len(runs),
                }
    summary = {
        "models": MODELS,
        "conditions": CONDITIONS,
        "n_tasks": len(TASK_NAMES),
        "cells": cells,
        "task_wrapper_lift": lift,
        "telemetry": tele_cells,
        "agent_wrapper_routing": _route(records, tele, "wrapped"),
        "agent_wrapper_routing_bare": _route(records, tele, "bare"),
    }
    LADDER.mkdir(parents=True, exist_ok=True)
    (LADDER / "records.json").write_text(json.dumps(records, indent=1), encoding="utf-8")
    (LADDER / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    _figures(cells, lift, summary["agent_wrapper_routing"])
    return summary


def _figures(cells: dict, lift: dict, routing: dict) -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    cats = [m.capitalize() for m in MODELS]
    # Fidelity ladder: completion by model, bare vs wrapped.
    save_svg(
        bar_chart(
            cats,
            {
                "bare prompt": [
                    cells[m].get("bare", {}).get("completion", 0.0) for m in MODELS],
                "task-wrapped": [
                    cells[m].get("wrapped", {}).get("completion", 0.0) for m in MODELS],
            },
            title="Capability ladder: task completion by model and wrapper",
            ylabel="completion (fraction of tasks fully passed)",
        ),
        FIGS / "ladder_completion.svg",
    )
    # Task-wrapper lift per model.
    if lift:
        save_svg(
            bar_chart(
                cats,
                {"completion lift": [lift.get(m, {}).get("completion_lift", 0.0) for m in MODELS]},
                title="Task-wrapper lift: completion gained from wrapping the task",
                ylabel="wrapped minus bare completion",
            ),
            FIGS / "ladder_wrapper_lift.svg",
        )
    # Cost vs fidelity with the routed operating point.
    series = {
        m.capitalize(): [(
            routing.get("per_task_cost_usd", {}).get(m, 0.0) * 1e6,
            cells[m].get("wrapped", {}).get("completion", 0.0),
        )] for m in MODELS if routing
    }
    if routing:
        routed_cost_per_task = routing["routed_cost_usd"] / max(1, len(TASK_NAMES))
        series["Routed (agent wrapper)"] = [(
            routed_cost_per_task * 1e6, routing["routed_completion"])]
        save_svg(
            line_chart(
                series,
                title="Agent wrapper: completion against cost (routing vs single model)",
                xlabel="USD per task x 1e6 (representative tiers)",
                ylabel="completion",
            ),
            FIGS / "ladder_cost_fidelity.svg",
        )


if __name__ == "__main__":
    s = analyse()
    r = s.get("agent_wrapper_routing", {})
    print(json.dumps({
        "cells": {m: {c: {"completion": round(s["cells"][m][c].get("completion", 0), 3),
                          "fidelity": round(s["cells"][m][c].get("fidelity", 0), 3)}
                      for c in CONDITIONS if s["cells"][m][c]} for m in MODELS},
        "task_wrapper_lift": s["task_wrapper_lift"],
        "routing": {k: r[k] for k in (
            "routed_completion", "always_top_completion", "cost_saving_multiple",
            "latency_saving_multiple", "choices") if k in r},
    }, indent=1))
