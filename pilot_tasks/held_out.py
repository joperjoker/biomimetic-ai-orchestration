"""Score the held-out expert tier and measure the task-wrapper lift on it.

Mirrors the primary ladder analysis (`pilot_tasks/ladder.py`) but on the
structurally independent `held_out_suite`, so the task-wrapper completion lift
here is directly comparable to the primary tier. Submissions live in
``results/live_pilot/held_out/{model}__{condition}__{k}.txt`` in the same block
format the ladder uses.
"""

from __future__ import annotations

import re
import signal
import statistics
from pathlib import Path

from cta.stats import bootstrap_ci
from pilot_tasks.held_out_suite import TASK_NAMES
from pilot_tasks.held_out_suite import score as ho_score

HELD_OUT = Path("results/live_pilot/held_out")
MODELS = ["haiku", "sonnet", "opus"]
CONDITIONS = ["bare", "wrapped"]

_BLOCK = re.compile(
    r"###\s*TASK:\s*(?P<name>\w+).*?CONFIDENCE:\s*(?P<conf>[0-9.]+).*?```(?:python)?\s*(?P<code>.*?)```",
    re.DOTALL | re.IGNORECASE,
)


class _Timeout(Exception):
    pass


def _run(name: str, code: str, timeout_s: int = 5) -> float:
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
        return ho_score(name, func)
    except Exception:
        return 0.0
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def load(path: str | Path = HELD_OUT) -> list[dict]:
    path = Path(path)
    records: list[dict] = []
    for f in sorted(path.glob("*.txt")):
        parts = f.stem.split("__")
        if len(parts) != 3:
            continue
        model, condition, _agent = parts
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
                    "task": name,
                    "confidence": float(m.group("conf")),
                    "pass_fraction": frac,
                    "passed": frac >= 1.0,
                }
            )
    return records


def _cell(records: list[dict], model: str, condition: str) -> dict:
    rows = [r for r in records if r["model"] == model and r["condition"] == condition]
    if not rows:
        return {}
    conf = [r["confidence"] for r in rows]
    succ = [1.0 if r["passed"] else 0.0 for r in rows]
    _, lo, hi = bootstrap_ci(succ)
    return {
        "attempts": len(rows),
        "agents": len(rows) // len(TASK_NAMES),
        "completion": statistics.mean(succ),
        "completion_ci": [lo, hi],
        "fidelity": statistics.mean(r["pass_fraction"] for r in rows),
        "mean_confidence": statistics.mean(conf),
        "overconfidence_gap": statistics.mean(conf) - statistics.mean(succ),
    }


def analyse(path: str | Path = HELD_OUT) -> dict:
    records = load(path)
    cells: dict = {}
    lift: dict = {}
    for m in MODELS:
        cells[m] = {}
        for c in CONDITIONS:
            cell = _cell(records, m, c)
            if cell:
                cells[m][c] = cell
        if "bare" in cells[m] and "wrapped" in cells[m]:
            lift[m] = round(
                cells[m]["wrapped"]["completion"] - cells[m]["bare"]["completion"], 4
            )
    return {"tasks": len(TASK_NAMES), "cells": cells, "task_wrapper_lift": lift}


if __name__ == "__main__":
    import json

    print(json.dumps(analyse(), indent=2, default=float))
