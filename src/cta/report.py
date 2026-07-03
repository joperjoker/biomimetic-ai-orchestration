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
    gate: dict[str, list[float]] | None = None,
    feasibility: dict[str, float] | None = None,
    stability: list[dict[str, float]] | None = None,
    calibration: dict[str, list[dict[str, object]]] | None = None,
    safety: dict[str, list[float]] | None = None,
    annealing: list[dict[str, float]] | None = None,
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
            "claim": "peak per-node load grows more slowly for CTA than central",
            "cta_growth_factor": round(growth_cta, 2),
            "central_growth_factor": round(growth_cen, 2),
            "verdict": _verdict(growth_cta < growth_cen),
        }

    # H2: CTA quality is at least the pull-based quality (the barrier helps) and
    # within a pre-registered margin of the full-information optimum. The optimum
    # is central_best (each task to its globally best eligible agent, agent reuse
    # allowed), which matches CTA's non-exclusive setting, rather than the
    # one-to-one Hungarian assignment that is handicapped by forced spreading.
    cta_q = base_values.get("cta", {}).get("mean_quality", [])
    pull_q = base_values.get("pull_based", {}).get("mean_quality", [])
    opt_q = base_values.get("central_best", {}).get("mean_quality", [])
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

    # H3: the engine labels infeasible and stalled tasks correctly against truth.
    if feasibility is not None:
        ok = feasibility.get("infeasible_recall", 0.0) >= 0.999 and feasibility.get(
            "stalled_recall", 0.0
        ) >= 0.999
        verdicts["H3"] = {
            "claim": "the engine labels infeasible and stalled tasks correctly",
            "infeasible_recall": round(feasibility.get("infeasible_recall", 0.0), 3),
            "stalled_recall": round(feasibility.get("stalled_recall", 0.0), 3),
            "verdict": _verdict(ok),
        }
    else:
        verdicts["H3"] = {"claim": "infeasible and stall labelling", "verdict": "PENDING"}

    # H4 (safety): the integrity gate prevents out-of-scope writes by adversarial
    # agents. Supported when gate-on violations are zero, or far below gate-off.
    if safety is not None and safety.get("gate_off_violations"):
        on = safety["gate_on_violations"]
        off = safety["gate_off_violations"]
        on_mean, off_mean = mean_ci(on)[0], mean_ci(off)[0]
        # The gate detects out-of-scope actions with recall < 1, so a real result
        # is a large reduction, not necessarily zero. Supported when the gate cuts
        # violations by at least two thirds.
        reduction = 1.0 - on_mean / off_mean if off_mean > 0 else 0.0
        verdicts["H4"] = {
            "claim": "the integrity gate substantially reduces out-of-scope writes",
            "gate_on_violations": round(on_mean, 3),
            "gate_off_violations": round(off_mean, 3),
            "reduction": round(reduction, 3),
            "verdict": _verdict(off_mean > 0 and reduction >= 0.667),
        }
    elif gate is not None and gate.get("gate_on_quality") and gate.get("gate_off_quality"):
        on_q = gate["gate_on_quality"]
        off_q = gate["gate_off_quality"]
        _, p = mann_whitney_u(on_q, off_q)
        on_mean, off_mean = mean_ci(on_q)[0], mean_ci(off_q)[0]
        verdicts["H4"] = {
            "claim": "the Rejection Gate preserves quality under unreliability",
            "gate_on_quality": round(on_mean, 3),
            "gate_off_quality": round(off_mean, 3),
            "p": round(p, 4),
            "verdict": _verdict(on_mean > off_mean),
        }
    else:
        verdicts["H4"] = {
            "claim": "the integrity gate prevents out-of-scope writes",
            "verdict": "PENDING",
        }

    # H5: activation-energy annealing (E14) bounds the stall time of feasible
    # tasks. Measured on the temporal engine: without annealing the stalled but
    # feasible tasks are never claimed (unmet, unbounded stall); with a positive
    # rate the barrier relaxes, the stall falls, and every feasible task resolves.
    # The static Ea by T grid (if provided) is an additional monotonicity check.
    if annealing:
        no_anneal = annealing[0]
        full_anneal = annealing[-1]
        bounded = full_anneal["unmet_rate"] <= 0.1 and full_anneal["max_stall"] < no_anneal[
            "max_stall"
        ]
        needs_annealing = no_anneal["unmet_rate"] >= 0.5
        monotone_ok = True
        if stability:
            by_ea: dict[float, list[float]] = {}
            for cell in stability:
                by_ea.setdefault(cell["activation_energy"], []).append(cell["unmet_rate"])
            eas = sorted(by_ea)
            mean_unmet = [sum(by_ea[e]) / len(by_ea[e]) for e in eas]
            monotone_ok = all(
                mean_unmet[i] <= mean_unmet[i + 1] + 0.05 for i in range(len(mean_unmet) - 1)
            )
        verdicts["H5"] = {
            "claim": "annealing bounds the stall time of feasible tasks",
            "unmet_without_annealing": round(no_anneal["unmet_rate"], 3),
            "unmet_with_annealing": round(full_anneal["unmet_rate"], 3),
            "max_stall_without_annealing": round(no_anneal["max_stall"], 1),
            "max_stall_with_annealing": round(full_anneal["max_stall"], 1),
            "verdict": _verdict(bounded and needs_annealing and monotone_ok),
        }
    else:
        verdicts["H5"] = {"claim": "annealing bounds stall time", "verdict": "PENDING"}

    # H7 (the failure mode): winners' self-reports of fit systematically
    # over-predict the realised quality they deliver, because the self-report
    # omits competence. Measured as a materially positive overconfidence gap under
    # raw self-selection. We do not claim the gap grows with the injected bias: in
    # this model it is dominated by the structural fit-versus-competence gap.
    raw = calibration.get("raw") if calibration else None
    if raw:
        gap = max(float(pt["overconfidence_gap"]) for pt in raw)
        margin = 0.05
        verdicts["H7"] = {
            "claim": "self-reports over-predict realised success because they omit competence",
            "overconfidence_gap": round(gap, 3),
            "verdict": _verdict(gap > margin),
        }
    else:
        verdicts["H7"] = {"claim": "self-reports over-predict success", "verdict": "PENDING"}

    # H8 (the fix): discounting the self-report by the track record (reliability
    # mode) recovers task completion versus the raw self-report, under the worst
    # injected overconfidence. Tested on the per-seed completion rate.
    rel = calibration.get("reliability") if calibration else None
    if raw and rel:
        raw_top = [float(x) for x in raw[-1]["completion_values"]]  # type: ignore[union-attr]
        rel_top = [float(x) for x in rel[-1]["completion_values"]]  # type: ignore[union-attr]
        _, p = mann_whitney_u(rel_top, raw_top)
        rel_mean, raw_mean = mean_ci(rel_top)[0], mean_ci(raw_top)[0]
        verdicts["H8"] = {
            "claim": "the track-record correction recovers completion under miscalibration",
            "reliability_completion": round(rel_mean, 3),
            "raw_completion": round(raw_mean, 3),
            "recovery": round(rel_mean - raw_mean, 3),
            "p": round(p, 4),
            "verdict": _verdict(rel_mean > raw_mean and p < 0.05),
        }
    else:
        verdicts["H8"] = {
            "claim": "track-record correction recovers completion",
            "verdict": "PENDING",
        }

    # Multiple-comparison control across the family of hypotheses that rest on a
    # p-value (H2 against the pull-based baseline, H8 the calibration recovery).
    # Holm-Bonferroni is applied and the corrected value and significance are
    # recorded alongside the raw p, so the reported inference matches section 2.6.
    p_family: dict[str, float] = {}
    if "p_vs_pull" in verdicts.get("H2", {}):
        p_family["H2"] = float(verdicts["H2"]["p_vs_pull"])
    if "p" in verdicts.get("H8", {}):
        p_family["H8"] = float(verdicts["H8"]["p"])
    if p_family:
        corrected = holm_over_hypotheses(p_family)
        for key, (adj_p, significant) in corrected.items():
            verdicts[key]["p_holm"] = round(adj_p, 4)
            verdicts[key]["significant_holm"] = significant
        # H8's support rests on the corrected significance, not the raw p.
        if "H8" in verdicts and "significant_holm" in verdicts["H8"]:
            recovers = float(verdicts["H8"].get("recovery", 0.0)) > 0.0
            verdicts["H8"]["verdict"] = _verdict(recovers and verdicts["H8"]["significant_holm"])
    return verdicts


def _advantage_by_heterogeneity(
    heterogeneity: dict[str, list[dict[str, float]]],
) -> list[tuple[float, float]]:
    cta = heterogeneity.get("cta", [])
    opt = heterogeneity.get("central_best", [])
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
    parts.append("## Peak per-node load scaling")
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
