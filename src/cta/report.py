"""Evaluate the hypotheses and write the results as Markdown.

Given per-seed metric values and the sweeps from the harness, this produces
verdicts for the hypotheses the current in-process engine can test (H1, H2, H6)
and marks the rest as pending the concurrent engine or the live pilot. It is
honest about scope: a verdict is "supported", "not supported", or "pending".
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from cta.stats import cliffs_delta, holm_bonferroni, mann_whitney_u, mean_ci


def _verdict(supported: bool) -> str:
    return "SUPPORTED" if supported else "NOT SUPPORTED"


def evaluate(
    base_values: dict[str, dict[str, list[float]]],
    scaling: dict[str, list[dict[str, float]]],
    heterogeneity: dict[str, list[dict[str, float]]],
) -> dict[str, dict[str, object]]:
    """Return a verdict record per hypothesis.

    ``base_values[condition]`` maps a metric name to the per-seed values at the
    base parameters. ``scaling`` and ``heterogeneity`` are the sweep outputs.
    """
    verdicts: dict[str, dict[str, object]] = {}

    # H1: coordinator work grows more slowly for CTA than for the central baseline.
    cta_cw = [p["mean"] for p in scaling.get("cta", [])]
    cen_cw = [p["mean"] for p in scaling.get("central_optimal", [])]
    if cta_cw and cen_cw:
        growth_cta = cta_cw[-1] / max(cta_cw[0], 1e-9)
        growth_cen = cen_cw[-1] / max(cen_cw[0], 1e-9)
        verdicts["H1"] = {
            "claim": "coordinator work grows more slowly for CTA than central",
            "cta_growth_factor": round(growth_cta, 2),
            "central_growth_factor": round(growth_cen, 2),
            "verdict": _verdict(growth_cta < growth_cen),
        }

    # H2: CTA quality is at least the pull-based quality (the barrier helps) and
    # within a pre-registered margin of the central optimum.
    cta_q = base_values.get("cta", {}).get("mean_quality", [])
    pull_q = base_values.get("pull_based", {}).get("mean_quality", [])
    opt_q = base_values.get("central_optimal", {}).get("mean_quality", [])
    if cta_q and pull_q and opt_q:
        _, p_pull = mann_whitney_u(cta_q, pull_q)
        cta_mean = mean_ci(cta_q)[0]
        opt_mean = mean_ci(opt_q)[0]
        margin = 0.05
        within = cta_mean >= opt_mean - margin
        not_worse_than_pull = cta_mean >= mean_ci(pull_q)[0] - 1e-9
        verdicts["H2"] = {
            "claim": "CTA quality is not worse than pull-based and within margin of the optimum",
            "cta_mean_quality": round(cta_mean, 3),
            "pull_mean_quality": round(mean_ci(pull_q)[0], 3),
            "optimal_mean_quality": round(opt_mean, 3),
            "cliffs_delta_vs_pull": round(cliffs_delta(cta_q, pull_q), 3),
            "p_vs_pull": round(p_pull, 4),
            "verdict": _verdict(within and not_worse_than_pull),
        }

    # H6: CTA's quality advantage over the central optimum grows with heterogeneity.
    adv = _advantage_by_heterogeneity(heterogeneity)
    if adv:
        low = adv[0][1]
        high = adv[-1][1]
        verdicts["H6"] = {
            "claim": "CTA advantage over the optimum increases with heterogeneity",
            "advantage_low_h": round(low, 3),
            "advantage_high_h": round(high, 3),
            "verdict": _verdict(high > low),
        }

    verdicts["H3"] = {
        "claim": "infeasible and stall labelling",
        "verdict": "PENDING (needs labelled generator ground truth)",
    }
    verdicts["H4"] = {
        "claim": "gate preserves integrity under unreliability",
        "verdict": "PENDING (needs the gate ablation run)",
    }
    verdicts["H5"] = {
        "claim": "stability across Ea and T",
        "verdict": "PENDING (needs the Ea by T sweep)",
    }
    return verdicts


def _advantage_by_heterogeneity(
    heterogeneity: dict[str, list[dict[str, float]]],
) -> list[tuple[float, float]]:
    cta = heterogeneity.get("cta", [])
    opt = heterogeneity.get("central_optimal", [])
    out: list[tuple[float, float]] = []
    for c_point, o_point in zip(cta, opt, strict=False):
        h = c_point.get("heterogeneity", 0.0)
        out.append((h, c_point["mean"] - o_point["mean"]))
    return out


def holm_over_hypotheses(pvalues: dict[str, float]) -> dict[str, tuple[float, bool]]:
    keys = list(pvalues.keys())
    adjusted = holm_bonferroni([pvalues[k] for k in keys])
    return {k: adjusted[i] for i, k in enumerate(keys)}


def _table(rows: Sequence[Sequence[object]], header: Sequence[str]) -> str:
    line = "| " + " | ".join(header) + " |"
    sep = "| " + " | ".join("---" for _ in header) + " |"
    body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows)
    return f"{line}\n{sep}\n{body}"


def write_results_md(
    path: str | Path,
    verdicts: dict[str, dict[str, object]],
    scaling: dict[str, list[dict[str, float]]],
    figures: Sequence[str],
) -> None:
    """Write a Results Markdown document from the verdicts and sweeps."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    parts = ["# Results (autorun)", ""]
    parts.append("These results are generated by `cta autorun`. They are reproducible from the")
    parts.append("committed configuration and seeds. Verdicts are supported, not supported, or")
    parts.append("pending.")
    parts.append("")
    parts.append("## Hypotheses")
    parts.append("")
    rows = [(k, v.get("verdict", ""), v.get("claim", "")) for k, v in sorted(verdicts.items())]
    parts.append(_table(rows, ["Hypothesis", "Verdict", "Claim"]))
    parts.append("")
    if figures:
        parts.append("## Figures")
        parts.append("")
        for fig in figures:
            parts.append(f"![{Path(fig).stem}]({fig})")
            parts.append("")
    parts.append("## Coordinator-work scaling")
    parts.append("")
    conditions = list(scaling.keys())
    ns = [pt["n_agents"] for pt in scaling[conditions[0]]] if conditions else []
    header = ["N"] + conditions
    table_rows = []
    for i, n in enumerate(ns):
        row = [n] + [round(scaling[c][i]["mean"], 1) for c in conditions]
        table_rows.append(row)
    if table_rows:
        parts.append(_table(table_rows, header))
    parts.append("")
    p.write_text("\n".join(parts), encoding="utf-8")
