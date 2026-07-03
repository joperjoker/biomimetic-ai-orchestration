"""Parse agent submissions and score them against the hidden cases.

A submission is the raw text an agent returned, with per-task blocks:

    ### TASK: <name>
    CONFIDENCE: <x>
    ```python
    <code>
    ```

For each block, the code is executed in a fresh namespace, the named function is
extracted, and its pass fraction on the hidden cases is computed. The result is a
list of (agent, task, confidence, pass_fraction, passed) records: real self-report
against real outcome.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pilot_tasks.suite import TASK_NAMES, score

_BLOCK = re.compile(
    r"###\s*TASK:\s*(?P<name>\w+).*?CONFIDENCE:\s*(?P<conf>[0-9.]+).*?```(?:python)?\s*(?P<code>.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def parse(text: str) -> list[tuple[str, float, str]]:
    out = []
    for m in _BLOCK.finditer(text):
        name = m.group("name").strip()
        if name not in TASK_NAMES:
            continue
        out.append((name, float(m.group("conf")), m.group("code")))
    return out


def _run(name: str, code: str) -> float:
    ns: dict = {}
    try:
        exec(code, ns)  # noqa: S102 - our own subagents' toy solutions, sandboxed
        func = ns.get(name)
        if not callable(func):
            return 0.0
        return score(name, func)
    except Exception:
        return 0.0


def score_dir(path: str | Path) -> list[dict]:
    records: list[dict] = []
    for f in sorted(Path(path).glob("*.txt")):
        agent = f.stem
        for name, conf, code in parse(f.read_text(encoding="utf-8")):
            frac = _run(name, code)
            records.append(
                {
                    "agent": agent,
                    "task": name,
                    "confidence": conf,
                    "pass_fraction": frac,
                    "passed": frac >= 1.0,
                }
            )
    return records


if __name__ == "__main__":
    recs = score_dir(sys.argv[1] if len(sys.argv) > 1 else "results/live_pilot/submissions")
    print(json.dumps(recs, indent=1))
