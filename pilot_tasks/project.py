"""Analyse the miniquery project runs: per-module, integration, and assembly.

Each model builds the whole project under a bare and a task-wrapped spec. We score
each module against its hidden cases in a shared namespace (so dependencies like
``select -> parse, match`` resolve), and the whole-project completion (every module
passes). Then we exercise the two wrappers:

- **Task wrapper**: bare vs wrapped project completion, per model.
- **Agent wrapper (assembly)**: route each module to the cheapest model whose
  reliability-corrected self-report clears the barrier, take that model's code for
  the module, assemble the pieces into one namespace, and score the integrated
  project. This is decomposition + routing + specialists: a swarm builds a working
  project, and the task wrapper's interface contract is what lets cross-model
  modules snap together.
"""

from __future__ import annotations

import json
import re
import signal
import statistics
from pathlib import Path

from cta.cost import PRICING
from pilot_tasks.project_suite import MODULE_NAMES, score_namespace

PROJECT = Path("results/live_pilot/project")
FIGS = Path("results/figures")

MODELS = ["haiku", "sonnet", "opus"]
TIER = {"haiku": "economy", "sonnet": "standard", "opus": "premium"}
CONDITIONS = ["bare", "wrapped"]
BARRIER = 0.7

# Match each fenced code block together with the confidence that precedes it. The
# module a block provides is detected from the def it defines, not the block label,
# so a submission that mislabels or lumps its blocks is still scored on its code.
_BLOCK = re.compile(
    r"CONFIDENCE:\s*(?P<conf>[0-9.]+).*?```(?:python)?\s*(?P<code>.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def _blended_rate(tier: str) -> float:
    lo, hi = PRICING[tier]
    return (lo + hi) / 2.0


class _Timeout(Exception):
    pass


def _guard(seconds: int = 5):
    def _h(signum, frame):
        raise _Timeout()
    old = signal.signal(signal.SIGALRM, _h)
    signal.alarm(seconds)
    return old


def _unguard(old) -> None:
    signal.alarm(0)
    signal.signal(signal.SIGALRM, old)


def parse_submission(text: str) -> dict[str, tuple[float, str]]:
    out: dict[str, tuple[float, str]] = {}
    for m in _BLOCK.finditer(text):
        conf, code = float(m.group("conf")), m.group("code")
        for mod in MODULE_NAMES:
            if mod not in out and re.search(rf"def\s+{mod}\s*\(", code):
                out[mod] = (conf, code)
    return out


def _build_ns(code_by_module: dict[str, str]) -> dict:
    """Exec every module's code into one shared namespace (dependencies resolve)."""
    ns: dict = {}
    old = _guard()
    try:
        for name in MODULE_NAMES:
            code = code_by_module.get(name)
            if code:
                try:
                    exec(code, ns)  # noqa: S102 - our own subagents' toy modules
                except Exception:
                    pass
    finally:
        _unguard(old)
    return ns


def _score_project(code_by_module: dict[str, str]) -> dict:
    ns = _build_ns(code_by_module)
    old = _guard()
    try:
        per_module = {name: score_namespace(ns, name) for name in MODULE_NAMES}
    finally:
        _unguard(old)
    completion = 1.0 if all(v >= 1.0 for v in per_module.values()) else 0.0
    integration = per_module.get("select", 0.0)  # select exercises parse+match together
    return {"per_module": per_module, "completion": completion, "integration": integration}


def _submissions(path: Path) -> dict:
    """{(model, condition): {module: (conf, code)}} using the first agent per cell."""
    subs: dict = {}
    for f in sorted(path.glob("*.txt")):
        parts = f.stem.split("__")
        if len(parts) != 3:
            continue
        model, condition, _ = parts
        key = (model, condition)
        if key not in subs:  # first agent wins as the code source
            subs[key] = parse_submission(f.read_text(encoding="utf-8"))
    return subs


def _telemetry(path: Path) -> dict:
    f = path / "telemetry.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _assemble(subs: dict, tele: dict, condition: str) -> dict:
    """Route each module to the cheapest capable model and score the assembly."""
    present = [m for m in MODELS if (m, condition) in subs]
    if len(present) < 2:
        return {}
    scored = {m: _score_project(_code(subs[(m, condition)])) for m in present}
    per_task_cost = {}
    for m in present:
        runs = [v for k, v in tele.items() if k.startswith(f"{m}__{condition}__")]
        if runs:
            toks = statistics.mean(v["tokens"] for v in runs)
            per_task_cost[m] = (toks / len(MODULE_NAMES)) / 1e6 * _blended_rate(TIER[m])

    reliab = {  # leave-one-module-out track record per model
        m: {
            mod: (statistics.mean(
                [scored[m]["per_module"][o] for o in MODULE_NAMES if o != mod]) or 0.0)
            for mod in MODULE_NAMES
        }
        for m in present
    }
    chosen, chosen_cost = {}, 0.0
    for mod in MODULE_NAMES:
        corrected = {
            m: subs[(m, condition)].get(mod, (0.0, ""))[0] * reliab[m][mod] for m in present
        }
        eligible = [m for m in present if corrected[m] >= BARRIER]
        pick = (min(eligible, key=lambda m: per_task_cost.get(m, 9e9)) if eligible
                else max(present, key=lambda m: corrected[m]))
        chosen[mod] = pick
        chosen_cost += per_task_cost.get(pick, 0.0)
    assembled = _score_project({mod: _code(subs[(chosen[mod], condition)]).get(mod, "")
                                for mod in MODULE_NAMES})
    top = MODELS[-1]
    top_cost = sum(per_task_cost.get(top, 0.0) for _ in MODULE_NAMES) if top in present else 0.0
    return {
        "condition": condition,
        "choices": chosen,
        "assembled_completion": assembled["completion"],
        "assembled_integration": assembled["integration"],
        "assembled_per_module": assembled["per_module"],
        "assembled_cost_usd": chosen_cost,
        "always_top_completion": scored.get(top, {}).get("completion", 0.0),
        "always_top_cost_usd": top_cost,
        "cost_saving_multiple": round(top_cost / chosen_cost, 2) if chosen_cost else 0.0,
        "single_model_completion": {m: scored[m]["completion"] for m in present},
    }


def _code(sub: dict) -> dict:
    return {name: sub[name][1] for name in sub}


def analyse(path: str | Path = PROJECT) -> dict:
    path = Path(path)
    subs = _submissions(path)
    tele = _telemetry(path)
    cells: dict = {}
    for m in MODELS:
        for c in CONDITIONS:
            if (m, c) in subs:
                sub = subs[(m, c)]
                res = _score_project(_code(sub))
                confs = [sub[k][0] for k in sub]
                cells.setdefault(m, {})[c] = {
                    "per_module": res["per_module"],
                    "completion": res["completion"],
                    "integration": res["integration"],
                    "mean_confidence": statistics.mean(confs) if confs else 0.0,
                    "modules_passed": sum(1 for v in res["per_module"].values() if v >= 1.0),
                }
    lift = {}
    for m in MODELS:
        b, w = cells.get(m, {}).get("bare"), cells.get(m, {}).get("wrapped")
        if b and w:
            lift[m] = {
                "completion_lift": w["completion"] - b["completion"],
                "modules_passed_lift": w["modules_passed"] - b["modules_passed"],
            }
    summary = {
        "models": MODELS,
        "conditions": CONDITIONS,
        "modules": MODULE_NAMES,
        "depends": {"select": ["parse", "match"]},
        "cells": cells,
        "task_wrapper_lift": lift,
        "assembly_wrapped": _assemble(subs, tele, "wrapped"),
        "assembly_bare": _assemble(subs, tele, "bare"),
    }
    path.mkdir(parents=True, exist_ok=True)
    (path / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    _figure(cells)
    return summary


def _figure(cells: dict) -> None:
    from cta.viz import bar_chart, save_svg
    FIGS.mkdir(parents=True, exist_ok=True)
    cats = [m.capitalize() for m in MODELS]
    save_svg(
        bar_chart(
            cats,
            {
                "bare": [cells.get(m, {}).get("bare", {}).get("modules_passed", 0) for m in MODELS],
                "task-wrapped": [
                    cells.get(m, {}).get("wrapped", {}).get("modules_passed", 0) for m in MODELS],
            },
            title="miniquery project: modules passing (of 5) by model and wrapper",
            ylabel="modules fully passing",
        ),
        FIGS / "project_modules.svg",
    )


if __name__ == "__main__":
    s = analyse()
    aw, ab = s.get("assembly_wrapped", {}), s.get("assembly_bare", {})
    print(json.dumps({
        "cells": {m: {c: {"completion": s["cells"][m][c]["completion"],
                          "modules_passed": s["cells"][m][c]["modules_passed"]}
                      for c in CONDITIONS if c in s["cells"].get(m, {})} for m in MODELS
                  if m in s["cells"]},
        "task_wrapper_lift": s["task_wrapper_lift"],
        "assembly_wrapped": {k: aw.get(k) for k in (
            "choices", "assembled_completion", "cost_saving_multiple",
            "single_model_completion")},
        "assembly_bare": {k: ab.get(k) for k in (
            "assembled_completion", "assembled_per_module")},
    }, indent=1))
