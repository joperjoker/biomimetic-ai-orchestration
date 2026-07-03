"""Analyse the live-pilot submissions into real calibration data and a figure.

Scores every agent submission against the hidden cases, writes the per-attempt
records and a summary (overconfidence gap, Brier, ECE, per-task pass rates), and
draws a reliability diagram of real self-report against real outcome. This is the
external-validity anchor: measured calibration of a real coding agent, comparable
to the reliability curves MarketBench reports.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from cta.engine import _brier_ece, reliability_bins
from cta.viz import line_chart, save_svg
from pilot_tasks.score_submissions import score_dir

SUBMISSIONS = "results/live_pilot/submissions"
OUT = Path("results/live_pilot")


def analyse() -> dict:
    records = score_dir(SUBMISSIONS)
    conf = [r["confidence"] for r in records]
    succ = [1.0 if r["passed"] else 0.0 for r in records]
    brier, ece = _brier_ece(conf, succ)
    by_task: dict[str, list[float]] = {}
    for r in records:
        by_task.setdefault(r["task"], []).append(1.0 if r["passed"] else 0.0)
    summary = {
        "attempts": len(records),
        "agents": len({r["agent"] for r in records}),
        "tasks": len(by_task),
        "mean_confidence": statistics.mean(conf) if conf else 0.0,
        "mean_success": statistics.mean(succ) if succ else 0.0,
        "overconfidence_gap": (statistics.mean(conf) - statistics.mean(succ)) if conf else 0.0,
        "brier": brier,
        "ece": ece,
        "per_task_pass_rate": {t: statistics.mean(v) for t, v in by_task.items()},
        "bins": reliability_bins(conf, succ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "records.json").write_text(json.dumps(records, indent=1), encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")

    # Reliability diagram: real confidence bins vs realised success, with the
    # diagonal of perfect calibration. Points above the diagonal are underconfident.
    bins = summary["bins"]
    series = {
        "real Claude agent": [
            (float(b["mean_prediction"]), float(b["accuracy"])) for b in bins
        ],
        "perfect calibration": [(0.0, 0.0), (1.0, 1.0)],
    }
    save_svg(
        line_chart(
            series,
            title="Live pilot: real agent calibration (predicted vs realised)",
            xlabel="stated confidence",
            ylabel="realised pass rate",
        ),
        Path("results/figures/reliability_live.svg"),
    )
    return summary


if __name__ == "__main__":
    s = analyse()
    print(json.dumps({k: v for k, v in s.items() if k != "bins"}, indent=1))
