"""Two-sided calibration curve from the OOD overconfidence tier plus the ladder.

The in-distribution ladder measured the Claude models as underconfident (high
confidence, high realised pass, points above the diagonal). The OOD suite
(``pilot_tasks/ood_suite.py``) supplies the missing overconfident arm:
solvable-but-trap-dense tasks where a bare prompt draws a confident answer that
slips on edge cases, so confidence exceeds the realised pass rate (points below
the diagonal). Combining both over the confidence axis gives a two-sided
reliability diagram.

Submissions live in ``results/live_pilot/ood/{model}__{condition}__{k}.txt`` in
the same block format the ladder uses. This module scores them against the OOD
references and, with the ladder records, draws the two-sided diagram.
"""

from __future__ import annotations

import re
import signal
import statistics
from pathlib import Path

from cta.engine import _brier_ece, reliability_bins
from cta.stats import bootstrap_ci
from cta.viz import line_chart, save_svg
from pilot_tasks import ladder as ladder_mod
from pilot_tasks.ood_suite import TASK_NAMES
from pilot_tasks.ood_suite import score as ood_score

OOD = Path("results/live_pilot/ood")
FIGS = Path("results/figures")
MODELS = ["haiku", "sonnet", "opus"]

_BLOCK = re.compile(
    r"###\s*TASK:\s*(?P<name>\w+).*?CONFIDENCE:\s*(?P<conf>[0-9.]+).*?```(?:python)?\s*(?P<code>.*?)```",
    re.DOTALL | re.IGNORECASE,
)


class _Timeout(Exception):
    pass


def _run(name: str, code: str, timeout_s: int = 5) -> float:
    """Execute a submitted OOD solution and score it, guarding against a hang."""
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
        return ood_score(name, func)
    except Exception:
        return 0.0
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def load(path: str | Path = OOD) -> list[dict]:
    """Parse every OOD submission into (model, condition, agent, task, ...) rows."""
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
                    "agent": f.stem,
                    "task": name,
                    "confidence": float(m.group("conf")),
                    "pass_fraction": frac,
                    "passed": frac >= 1.0,
                }
            )
    return records


def _cell(records: list[dict], model: str) -> dict:
    rows = [r for r in records if r["model"] == model]
    if not rows:
        return {}
    conf = [r["confidence"] for r in rows]
    succ = [1.0 if r["passed"] else 0.0 for r in rows]
    brier, ece = _brier_ece(conf, succ)
    _, lo, hi = bootstrap_ci(succ)
    return {
        "attempts": len(rows),
        "completion": statistics.mean(succ),
        "completion_ci": [lo, hi],
        "mean_confidence": statistics.mean(conf),
        "overconfidence_gap": statistics.mean(conf) - statistics.mean(succ),
        "brier": brier,
        "ece": ece,
    }


def analyse(path: str | Path = OOD) -> dict:
    """Score the OOD tier and build the two-sided reliability diagram."""
    records = load(path)
    per_model = {m: _cell(records, m) for m in MODELS if _cell(records, m)}

    ood_conf = [r["confidence"] for r in records]
    ood_succ = [1.0 if r["passed"] else 0.0 for r in records]

    ladder_records = ladder_mod.load()
    lad_conf = [r["confidence"] for r in ladder_records]
    lad_succ = [1.0 if r["passed"] else 0.0 for r in ladder_records]

    combined_conf = ood_conf + lad_conf
    combined_succ = ood_succ + lad_succ

    summary = {
        "per_model": per_model,
        "ood_attempts": len(records),
        "ood_overconfidence_gap": (
            statistics.mean(ood_conf) - statistics.mean(ood_succ) if records else 0.0
        ),
        "ladder_attempts": len(ladder_records),
        "ladder_overconfidence_gap": (
            statistics.mean(lad_conf) - statistics.mean(lad_succ) if ladder_records else 0.0
        ),
        "two_sided": bool(records and ladder_records),
        "bins_combined": reliability_bins(combined_conf, combined_succ),
    }

    if records:
        _figure(ood_conf, ood_succ, lad_conf, lad_succ)
    return summary


def _figure(ood_conf, ood_succ, lad_conf, lad_succ) -> None:
    """Two-sided reliability diagram: the OOD (overconfident) and ladder
    (underconfident) arms against the diagonal of perfect calibration."""
    series = {"perfect calibration": [(0.0, 0.0), (1.0, 1.0)]}
    ood_bins = reliability_bins(ood_conf, ood_succ)
    if ood_bins:
        series["OOD tier (overconfident arm)"] = [
            (b["mean_prediction"], b["accuracy"]) for b in ood_bins
        ]
    if lad_conf:
        lad_bins = reliability_bins(lad_conf, lad_succ)
        if lad_bins:
            series["in-distribution ladder (underconfident arm)"] = [
                (b["mean_prediction"], b["accuracy"]) for b in lad_bins
            ]
    FIGS.mkdir(parents=True, exist_ok=True)
    save_svg(
        line_chart(
            series,
            title="Two-sided calibration: stated confidence vs realised pass rate",
            xlabel="stated confidence",
            ylabel="realised pass rate",
        ),
        FIGS / "calibration_two_sided.svg",
    )


if __name__ == "__main__":
    import json

    print(json.dumps(analyse(), indent=2, default=float))
