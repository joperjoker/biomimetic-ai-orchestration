"""The ``cta`` command line, including the autonomous run.

``cta autorun`` executes the pre-registered sweeps across the four conditions,
computes the statistics, writes a results summary and figures, evaluates the
hypotheses, and prints a short report. It is deterministic and needs no external
service, so "start" is a single command.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from cta.dashboard import write_dashboard
from cta.dataset import dump_runs
from cta.generators import generate_agents, generate_tasks
from cta.harness import (
    CONDITIONS,
    CellParams,
    Protocol,
    annealing_curve,
    bounded_vs_cta,
    calibration_sweep,
    feasibility_check,
    gate_ablation,
    h2_decomposition,
    heterogeneity_sweep,
    recovery_surface,
    recovery_vs_spread,
    reduction_vs_recall,
    run_seeds,
    safety_ablation,
    scaling_sweep,
    stability_grid,
    temporal_metrics,
    track_record_sweep,
)
from cta.pilot import MockClient, run_pilot
from cta.realism import adversarial_fleet_safety, fleet_experiment, fleet_mix_sweep
from cta.report import evaluate, write_results_md
from cta.stats import bootstrap_ci, mean_ci
from cta.viz import bar_chart, heatmap, line_chart, save_svg


def _demo_protocol() -> Protocol:
    return Protocol(
        seeds=5,
        base=CellParams(n_agents=60, n_tasks=48, n_domains=4, heterogeneity=0.8),
        scaling_n=(40, 80, 160, 320),
        heterogeneity_grid=(0.0, 0.5, 1.0),
    )


def _family_verdicts(protocol: Protocol, family: str) -> dict[str, dict[str, object]]:
    """Verdicts for the population-dependent hypotheses under a generator family.

    Re-runs the quality (H2), safety (H4), and calibration (H7, H8) evidence under
    the given generative structure, so the robustness pass can compare verdicts
    across families. H1 is structural (peak load is `N` times `M` by construction),
    so it is not re-run here.
    """
    base_f = replace(protocol.base, family=family)
    base_values = {
        c: {"mean_quality": [r["mean_quality"] for r in run_seeds(c, base_f, protocol.seeds)]}
        for c in ("cta", "pull_based", "central_best")
    }
    calibration = calibration_sweep(base_f, protocol.seeds)
    safety = safety_ablation(base_f, protocol.seeds)
    verdicts = evaluate(base_values, {}, {}, calibration=calibration, safety=safety)
    return {h: verdicts[h] for h in ("H2", "H4", "H7", "H8") if h in verdicts}


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
    track_record = track_record_sweep(protocol.base, protocol.seeds)
    # Sensitivity sweeps (bands, not single points).
    recovery_spread = recovery_vs_spread(protocol.base, protocol.seeds)
    recovery_grid = recovery_surface(protocol.base, protocol.seeds)
    gate_recall_sweep = reduction_vs_recall(protocol.base, protocol.seeds)
    h2_gap = h2_decomposition(protocol.base, protocol.seeds)
    # Bounded-information central baseline: the fair, beatable form of H6 (P1.0).
    bounded = bounded_vs_cta(protocol.base, protocol.seeds)
    # Realistic fleet grounded in measured LLM calibration (MarketBench archetypes).
    fleet = fleet_experiment(seeds=protocol.seeds)
    fleet_mix = fleet_mix_sweep(seeds=protocol.seeds)
    fleet_safety = adversarial_fleet_safety(seeds=protocol.seeds)
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
        bounded,
    )

    # Generalisability: re-run the population-dependent hypotheses under a second,
    # structurally different generator and compare the verdicts (section 2.7).
    latent_verdicts = _family_verdicts(protocol, "latent")
    robustness = {
        "domains": {h: verdicts[h].get("verdict") for h in ("H2", "H4", "H7", "H8")},
        "latent": {h: latent_verdicts[h].get("verdict") for h in latent_verdicts},
        "latent_detail": latent_verdicts,
    }

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

    # Track-record figure: raw and reliability completion versus history length.
    track_series = {
        "raw self-report": [(float(p["window"]), float(p["raw_completion"])) for p in track_record],
        "reliability correction": [
            (float(p["window"]), float(p["reliability_completion"])) for p in track_record
        ],
    }
    save_svg(
        line_chart(
            track_series,
            title="Completion recovery vs track-record length",
            xlabel="track-record length (prior attempts)",
            ylabel="task completion rate",
        ),
        figures_dir / "track_record_recovery.svg",
    )

    # Sensitivity: recovery versus competence spread, and violation reduction
    # versus gate recall (bands, not single points).
    save_svg(
        line_chart(
            {"recovery": [(float(p["spread"]), float(p["recovery"])) for p in recovery_spread]},
            title="Recovery vs competence spread",
            xlabel="competence spread (1 - capability floor)",
            ylabel="completion recovery",
        ),
        figures_dir / "recovery_vs_spread.svg",
    )
    recall_pts = [(float(p["gate_recall"]), float(p["reduction"])) for p in gate_recall_sweep]
    save_svg(
        line_chart(
            {"reduction": recall_pts},
            title="Violation reduction vs gate recall",
            xlabel="gate detection recall",
            ylabel="violation reduction",
        ),
        figures_dir / "gate_recall.svg",
    )
    # Surface: recovery over overconfidence bias by competence spread (a heatmap).
    save_svg(
        heatmap(
            recovery_grid["recovery"],
            row_labels=[f"bias {b}" for b in recovery_grid["biases"]],
            col_labels=[f"low {low}" for low in recovery_grid["lows"]],
            title="Recovery: overconfidence bias by competence spread",
            xlabel="capability floor (lower is wider spread)",
            ylabel="overconfidence bias",
        ),
        figures_dir / "calibration_surface.svg",
    )
    # Generalisability: a numeric comparison across the two generator families.
    dq = base_values["cta"]["mean_quality"]
    lq = robustness["latent_detail"].get("H2", {}).get("cta_mean_quality", 0.0)
    save_svg(
        bar_chart(
            categories=["CTA quality", "H8 recovery", "H4 reduction"],
            series={
                "domains": [
                    round(mean_ci(dq)[0], 3),
                    float(verdicts["H8"].get("recovery", 0.0)),
                    float(verdicts["H4"].get("reduction", 0.0)),
                ],
                "latent": [
                    float(lq),
                    float(robustness["latent_detail"].get("H8", {}).get("recovery", 0.0)),
                    float(robustness["latent_detail"].get("H4", {}).get("reduction", 0.0)),
                ],
            },
            title="Key outcomes across generator families",
            ylabel="value",
        ),
        figures_dir / "robustness_bars.svg",
    )
    # H2 gap decomposition: deployed cost-aware CTA, a quality-first CTA, and the
    # full-information optimum, so the quality shortfall is attributed to its cause.
    save_svg(
        bar_chart(
            categories=["deployed (cost-aware)", "quality-first", "optimum"],
            series={
                "mean quality": [
                    round(float(h2_gap["reliability_quality"]), 3),
                    round(float(h2_gap["quality_mode_quality"]), 3),
                    round(float(h2_gap["optimum_quality"]), 3),
                ]
            },
            title="H2 gap: cost-awareness vs the competence proxy",
            ylabel="mean realised quality",
        ),
        figures_dir / "h2_decomposition.svg",
    )
    # Bounded-central figure: CTA versus an information-bounded central scheduler
    # as its reliability table goes stale (H9). CTA is flat; the central scheduler
    # starts ahead with fresh information and falls away as staleness rises.
    bounded_series = {
        "CTA (decentralised)": [
            (float(p["staleness"]), float(p["cta_quality"])) for p in bounded
        ],
        "central (bounded info)": [
            (float(p["staleness"]), float(p["bounded_quality"])) for p in bounded
        ],
    }
    save_svg(
        line_chart(
            bounded_series,
            title="CTA vs a central scheduler with a stale reliability table",
            xlabel="coordinator reliability staleness",
            ylabel="mean realised quality",
        ),
        figures_dir / "bounded_central.svg",
    )
    # Reliability diagram of the realistic fleet: mean predicted vs realised
    # success, with the diagonal of perfect calibration. Points below the diagonal
    # are overconfident. The correction pulls the retained winners toward it.
    reliability_series = {
        "raw self-report": [
            (float(b["mean_prediction"]), float(b["accuracy"])) for b in fleet["bins_raw"]
        ],
        "reliability correction": [
            (float(b["mean_prediction"]), float(b["accuracy"])) for b in fleet["bins_reliability"]
        ],
        "perfect calibration": [(0.0, 0.0), (1.0, 1.0)],
    }
    save_svg(
        line_chart(
            reliability_series,
            title="Fleet calibration: predicted vs realised success",
            xlabel="mean predicted success",
            ylabel="realised success rate",
        ),
        figures_dir / "reliability_diagram.svg",
    )
    # Fleet-mix sweep: recovery as the fleet's overconfident fraction rises.
    save_svg(
        line_chart(
            {
                "recovery": [
                    (float(p["overconfident_fraction"]), float(p["recovery"])) for p in fleet_mix
                ]
            },
            title="Recovery across fleet composition",
            xlabel="fraction of overconfident agents",
            ylabel="completion recovery",
        ),
        figures_dir / "fleet_mix.svg",
    )

    figures = [
        "figures/scaling_peak_per_node.svg",
        "figures/heterogeneity_quality.svg",
        "figures/calibration_quality.svg",
        "figures/annealing_stall.svg",
        "figures/track_record_recovery.svg",
        "figures/recovery_vs_spread.svg",
        "figures/gate_recall.svg",
        "figures/calibration_surface.svg",
        "figures/robustness_bars.svg",
        "figures/h2_decomposition.svg",
        "figures/bounded_central.svg",
        "figures/reliability_diagram.svg",
        "figures/fleet_mix.svg",
    ]
    write_results_md(out / "RESULTS.md", verdicts, scaling, figures)

    summary = {
        "protocol": {
            "seeds": protocol.seeds,
            "scaling_n": list(protocol.scaling_n),
            "heterogeneity_grid": list(protocol.heterogeneity_grid),
        },
        "base_quality": {
            c: dict(
                zip(("mean", "ci_low", "ci_high"), bootstrap_ci(v["mean_quality"]), strict=False)
            )
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
        "track_record": track_record,
        "recovery_vs_spread": recovery_spread,
        "recovery_surface": recovery_grid,
        "reduction_vs_recall": gate_recall_sweep,
        "h2_decomposition": h2_gap,
        "bounded_vs_cta": bounded,
        "fleet": {"experiment": fleet, "mix_sweep": fleet_mix, "safety": fleet_safety},
        "robustness": robustness,
        "verdicts": verdicts,
    }
    (out).mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_dashboard(out, out / "dashboard.html")
    # Release the raw per-run rows behind the aggregates as CSV (P1.3).
    dump_runs(str(out), protocol)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cta", description="Chemotactic Task Allocation")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("autorun", help="run the autonomous research protocol")
    run.add_argument("--out", default="results", help="output directory")
    run.add_argument("--full", action="store_true", help="run the full protocol (slower)")
    dash = sub.add_parser("dashboard", help="rebuild the HTML dashboard from an existing run")
    dash.add_argument("--out", default="results", help="results directory to read")
    dash.add_argument("--to", default="results/dashboard.html", help="dashboard output path")
    ds = sub.add_parser("dataset", help="write the raw per-run dataset to results/dataset/runs.csv")
    ds.add_argument("--out", default="results", help="output directory")
    ds.add_argument("--full", action="store_true", help="use the full protocol (more seeds)")
    pil = sub.add_parser("pilot", help="run the Stage 2 pilot pipeline (mock client, no calls)")
    pil.add_argument("--agents", type=int, default=20, help="number of agents")
    pil.add_argument("--tasks", type=int, default=15, help="number of tasks")
    pil.add_argument("--seed", type=int, default=0, help="random seed")
    args = parser.parse_args(argv)

    if args.command == "autorun":
        summary = autorun(args.out, demo=not args.full)
        print("autorun complete. Verdicts:")
        for h, v in sorted(summary["verdicts"].items()):
            print(f"  {h}: {v.get('verdict')}")
        print(f"Artifacts written to {args.out}/ (summary.json, RESULTS.md, figures/, dashboard).")
        return 0
    if args.command == "dashboard":
        path = write_dashboard(args.out, args.to)
        print(f"Dashboard written to {path}")
        return 0
    if args.command == "dataset":
        protocol = None if args.full else _demo_protocol()
        path = dump_runs(args.out, protocol)
        print(f"Dataset written to {path}")
        return 0
    if args.command == "pilot":
        import random

        agents = generate_agents(args.agents, 4, 0.8, random.Random(args.seed))
        tasks = generate_tasks(args.tasks, 4, random.Random(args.seed + 10_000), 0.2)
        result = run_pilot(agents, tasks, MockClient(seed=args.seed))
        print("pilot complete (mock client, no model calls). Summary:")
        for k, v in result.summary().items():
            print(f"  {k}: {v}")
        print("Swap MockClient for ClaudeAgentClient to run live (opt-in, budget-gated).")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
