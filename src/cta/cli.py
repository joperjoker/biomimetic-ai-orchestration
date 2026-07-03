"""The ``cta`` command line, including the autonomous run.

``cta autorun`` executes the pre-registered sweeps across the four conditions,
computes the statistics, writes a results summary and figures, evaluates the
hypotheses, and prints a short report. It is deterministic and needs no external
service, so "start" is a single command.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cta.harness import (
    CONDITIONS,
    CellParams,
    Protocol,
    annealing_curve,
    calibration_sweep,
    feasibility_check,
    gate_ablation,
    heterogeneity_sweep,
    run_seeds,
    safety_ablation,
    scaling_sweep,
    stability_grid,
    temporal_metrics,
)
from cta.report import evaluate, write_results_md
from cta.stats import mean_ci
from cta.viz import line_chart, save_svg


def _demo_protocol() -> Protocol:
    return Protocol(
        seeds=5,
        base=CellParams(n_agents=60, n_tasks=48, n_domains=4, heterogeneity=0.8),
        scaling_n=(40, 80, 160, 320),
        heterogeneity_grid=(0.0, 0.5, 1.0),
    )


def autorun(
    out_dir: str, demo: bool = True, protocol: Protocol | None = None
) -> dict[str, object]:
    if protocol is None:
        protocol = _demo_protocol() if demo else Protocol()
    out = Path(out_dir)
    figures_dir = out / "figures"

    # Per-seed base values for the quality comparisons (H2).
    base_values: dict[str, dict[str, list[float]]] = {}
    for cond in CONDITIONS:
        rows = run_seeds(cond, protocol.base, protocol.seeds)
        base_values[cond] = {"mean_quality": [r["mean_quality"] for r in rows]}

    scaling = scaling_sweep(CONDITIONS, protocol, metric="peak_per_node")
    hetero = heterogeneity_sweep(("cta", "central_best"), protocol, metric="mean_quality")

    # Figures (pure SVG).
    scaling_series = {
        c: [(pt["n_agents"], pt["mean"]) for pt in scaling[c]] for c in scaling
    }
    save_svg(
        line_chart(
            scaling_series,
            title="Peak per-node load vs agent count",
            xlabel="agents (log scale)",
            ylabel="peak per-node load",
            logx=True,
        ),
        figures_dir / "scaling_peak_per_node.svg",
    )
    hetero_series = {
        c: [(pt["heterogeneity"], pt["mean"]) for pt in hetero[c]] for c in hetero
    }
    save_svg(
        line_chart(
            hetero_series,
            title="Match quality vs heterogeneity",
            xlabel="agent heterogeneity",
            ylabel="mean quality",
        ),
        figures_dir / "heterogeneity_quality.svg",
    )

    gate = gate_ablation(protocol.base, protocol.seeds)
    feasibility = feasibility_check(protocol.base)
    stability = stability_grid(protocol.base, max(2, protocol.seeds // 2))
    calibration = calibration_sweep(protocol.base, protocol.seeds)
    safety = safety_ablation(protocol.base, protocol.seeds)
    annealing = annealing_curve(protocol.base, protocol.seeds)
    temporal = temporal_metrics(protocol.base, protocol.seeds)
    verdicts = evaluate(
        base_values,
        scaling,
        hetero,
        gate,
        feasibility,
        stability,
        calibration,
        safety,
        annealing,
    )

    # Calibration figure: task completion versus overconfidence, one line per mode.
    calibration_series = {
        mode: [(float(pt["bias"]), float(pt["completion_rate"])) for pt in points]
        for mode, points in calibration.items()
    }
    save_svg(
        line_chart(
            calibration_series,
            title="Task completion vs self-assessment overconfidence",
            xlabel="self-report bias (overconfidence)",
            ylabel="task completion rate",
        ),
        figures_dir / "calibration_quality.svg",
    )

    # Annealing figure: maximum stall time falls as the annealing rate rises (E14).
    annealing_series = {
        "max stall (rounds)": [(float(pt["rate"]), float(pt["max_stall"])) for pt in annealing],
    }
    save_svg(
        line_chart(
            annealing_series,
            title="Stall time bounded by activation-energy annealing",
            xlabel="annealing rate",
            ylabel="maximum stall (rounds)",
        ),
        figures_dir / "annealing_stall.svg",
    )

    figures = [
        "figures/scaling_peak_per_node.svg",
        "figures/heterogeneity_quality.svg",
        "figures/calibration_quality.svg",
        "figures/annealing_stall.svg",
    ]
    write_results_md(out / "RESULTS.md", verdicts, scaling, figures)

    summary = {
        "protocol": {
            "seeds": protocol.seeds,
            "scaling_n": list(protocol.scaling_n),
            "heterogeneity_grid": list(protocol.heterogeneity_grid),
        },
        "base_quality": {
            c: dict(zip(("mean", "ci_low", "ci_high"), mean_ci(v["mean_quality"]), strict=False))
            for c, v in base_values.items()
        },
        "scaling_peak_per_node": scaling,
        "heterogeneity_quality": hetero,
        "gate_ablation": gate,
        "feasibility": feasibility,
        "stability": stability,
        "calibration": calibration,
        "safety": safety,
        "annealing": annealing,
        "temporal": temporal,
        "verdicts": verdicts,
    }
    (out).mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cta", description="Chemotactic Task Allocation")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("autorun", help="run the autonomous research protocol")
    run.add_argument("--out", default="results", help="output directory")
    run.add_argument("--full", action="store_true", help="run the full protocol (slower)")
    args = parser.parse_args(argv)

    if args.command == "autorun":
        summary = autorun(args.out, demo=not args.full)
        print("autorun complete. Verdicts:")
        for h, v in sorted(summary["verdicts"].items()):
            print(f"  {h}: {v.get('verdict')}")
        print(f"Artifacts written to {args.out}/ (summary.json, RESULTS.md, figures/).")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
