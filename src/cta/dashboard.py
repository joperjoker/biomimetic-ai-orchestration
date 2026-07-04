"""Render the autorun results as a single self-contained HTML dashboard.

Reads ``results/summary.json`` and the committed SVG figures and inlines them into
one theme-aware page, so the verdicts, the generalisability comparison, and every
figure can be read at a glance. Pure standard library; no external assets, so the
page renders anywhere and needs no network.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

_CSS = """
:root {
  --bg: #fbfcfd; --panel: #ffffff; --ink: #14181d; --muted: #5b6672;
  --line: #e4e9ee; --accent: #2f6f9f; --ok: #2f7d57; --ok-bg: #e7f3ec;
  --no: #b46a22; --no-bg: #f8efe2; --pend: #6b7580; --pend-bg: #eef1f4;
  --mono: ui-monospace, "SFMono-Regular", "Cascadia Code", Menlo, monospace;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0e1216; --panel: #161c22; --ink: #e6ebf0; --muted: #8a97a5;
    --line: #263039; --accent: #6bb2df; --ok: #5cbe8a; --ok-bg: #16281f;
    --no: #d99a52; --no-bg: #2a2013; --pend: #8a97a5; --pend-bg: #1b2229;
  }
}
:root[data-theme="dark"] {
  --bg: #0e1216; --panel: #161c22; --ink: #e6ebf0; --muted: #8a97a5;
  --line: #263039; --accent: #6bb2df; --ok: #5cbe8a; --ok-bg: #16281f;
  --no: #d99a52; --no-bg: #2a2013; --pend: #8a97a5; --pend-bg: #1b2229;
}
:root[data-theme="light"] {
  --bg: #fbfcfd; --panel: #ffffff; --ink: #14181d; --muted: #5b6672;
  --line: #e4e9ee; --accent: #2f6f9f; --ok: #2f7d57; --ok-bg: #e7f3ec;
  --no: #b46a22; --no-bg: #f8efe2; --pend: #6b7580; --pend-bg: #eef1f4;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--sans);
  line-height: 1.55; }
.wrap { max-width: 1120px; margin: 0 auto; padding: 48px 24px 80px; }
.eyebrow { font-family: var(--mono); font-size: 12px; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--accent); margin: 0 0 10px; }
h1 { font-size: clamp(28px, 4vw, 40px); line-height: 1.1; margin: 0 0 12px;
  text-wrap: balance; letter-spacing: -0.01em; }
.thesis { max-width: 64ch; color: var(--muted); font-size: 17px; margin: 0 0 24px; }
.tally { display: flex; flex-wrap: wrap; gap: 10px; margin: 0 0 8px; }
.chip { font-family: var(--mono); font-size: 13px; padding: 6px 12px; border-radius: 999px;
  border: 1px solid var(--line); background: var(--panel); }
.chip b { color: var(--accent); }
h2 { font-size: 13px; font-family: var(--mono); letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--muted); margin: 56px 0 18px; padding-bottom: 8px; border-bottom: 1px solid var(--line); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px; }
.card .top { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.hid { font-family: var(--mono); font-weight: 700; font-size: 15px; }
.claim { margin: 8px 0 12px; font-size: 15px; }
.pill { font-family: var(--mono); font-size: 12px; font-weight: 700; padding: 4px 10px;
  border-radius: 999px; white-space: nowrap; letter-spacing: 0.02em; }
.pill.ok { color: var(--ok); background: var(--ok-bg); }
.pill.no { color: var(--no); background: var(--no-bg); }
.pill.pend { color: var(--pend); background: var(--pend-bg); }
.stats { display: flex; flex-wrap: wrap; gap: 6px 16px; font-family: var(--mono); font-size: 12.5px;
  color: var(--muted); font-variant-numeric: tabular-nums; }
.stats b { color: var(--ink); font-weight: 600; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); }
th { font-family: var(--mono); font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--muted); font-weight: 600; }
td.h { font-family: var(--mono); font-weight: 700; }
.figs { display: grid; grid-template-columns: repeat(auto-fill, minmax(440px, 1fr)); gap: 20px; }
figure { margin: 0; background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
  padding: 14px; }
figure .scroll { overflow-x: auto; }
figure svg { max-width: 100%; height: auto; display: block; margin: 0 auto; }
figcaption { margin-top: 10px; font-size: 13.5px; color: var(--muted); }
figcaption b { color: var(--ink); font-weight: 600; }
footer { margin-top: 56px; padding-top: 18px; border-top: 1px solid var(--line);
  font-family: var(--mono); font-size: 12.5px; color: var(--muted); }
"""

# Ordered hypotheses with a short human label and the summary keys worth surfacing.
_HYPS = [
    ("H1", "Scaling: peak per-node load", ["cta_growth_factor", "central_growth_factor"]),
    ("H2", "Quality vs the fair optimum", ["cta_mean_quality", "optimal_mean_quality"]),
    ("H3", "Infeasible vs stalled labelling", ["infeasible_recall", "stalled_recall"]),
    ("H4", "Safety gate reduces violations", ["gate_on_violations", "gate_off_violations", "reduction"]),
    ("H5", "Annealing bounds stall time", ["max_stall_without_annealing", "max_stall_with_annealing"]),
    ("H6", "Advantage vs heterogeneity", ["advantage_low_h", "advantage_high_h"]),
    ("H7", "Self-reports over-predict success", ["overconfidence_gap", "winner_brier", "winner_ece"]),
    ("H8", "Track record recovers completion", ["raw_completion", "reliability_completion", "recovery", "p_holm"]),
]

# Figures in reading order, with captions.
_FIGS = [
    ("scaling_peak_per_node.svg", "Peak per-node load stays flat for CTA as the population grows, while the central scheduler grows as N times M."),
    ("calibration_quality.svg", "Task completion versus self-assessment overconfidence, for the raw, reliability, and full-information selection modes."),
    ("track_record_recovery.svg", "The track-record correction recovers completion; even a short history helps, and it improves with length."),
    ("recovery_vs_spread.svg", "The correction's recovery grows with competence spread: it matters most where agents genuinely differ."),
    ("calibration_surface.svg", "Recovery over the overconfidence bias by competence spread. The bands are horizontal: spread drives the gap, not bias."),
    ("gate_recall.svg", "The safety result degrades gracefully with the gate's detection recall, rather than depending on a perfect detector."),
    ("annealing_stall.svg", "Activation-energy annealing bounds the stall time of feasible tasks; without it they are never claimed."),
    ("robustness_bars.svg", "Key outcomes under two structurally different generator families; the calibration and safety results hold in both."),
    ("h2_decomposition.svg", "The H2 quality gap: a quality-first CTA reaches the optimum's neighbourhood; the deployed cost-aware CTA gives up quality for lower latency by design."),
    ("bounded_central.svg", "H9: against an information-bounded central scheduler, CTA is level when the coordinator's reliability table is fresh and overtakes it as the table goes stale, because a decentralised agent never pays the central synchronisation lag."),
    ("biomimicry_ablation.svg", "Biomimicry ablation: removing the integrity gate multiplies out-of-scope violations while the activation barrier is quality-neutral in the batch regime (its role is liveness and the infeasible and stalled semantics). It isolates what each biological mechanism contributes."),
    ("reliability_diagram.svg", "A realistic fleet grounded in measured LLM calibration (MarketBench archetypes): predicted vs realised success. Points below the diagonal are overconfident; the correction pulls the retained winners toward it."),
    ("fleet_mix.svg", "The track-record correction keeps recovering completion across every realistic fleet composition, from all-calibrated to all-overconfident."),
    ("reliability_live.svg", "Live pilot: a real Claude coding agent over 13 tasks x 3 runs. Its points sit above the diagonal (stated ~0.92, delivered 1.0), so it is underconfident, consistent with the well-calibrated Claude models MarketBench reports."),
    ("heterogeneity_quality.svg", "Match quality across agent heterogeneity for CTA and the full-information optimum."),
]


def _pill(verdict: str) -> str:
    cls = {"SUPPORTED": "ok", "NOT SUPPORTED": "no"}.get(verdict, "pend")
    return f'<span class="pill {cls}">{html.escape(verdict or "PENDING")}</span>'


def _fmt(v: object) -> str:
    if isinstance(v, float):
        return f"{v:.3g}"
    return html.escape(str(v))


def build_dashboard(summary: dict, figures_dir: str | Path) -> str:
    figures_dir = Path(figures_dir)
    verdicts = summary.get("verdicts", {})
    supported = sum(1 for v in verdicts.values() if v.get("verdict") == "SUPPORTED")
    total = len(verdicts)
    robustness = summary.get("robustness", {})
    proto = summary.get("protocol", {})
    seeds = proto.get("seeds", "?")
    ns = proto.get("scaling_n", [])
    n_hi = max(ns) if ns else "?"

    cards = []
    for hid, label, keys in _HYPS:
        v = verdicts.get(hid, {})
        claim = html.escape(str(v.get("claim", label)))
        stats = " ".join(
            f"<span><b>{html.escape(k.replace('_', ' '))}</b> {_fmt(v[k])}</span>"
            for k in keys
            if k in v
        )
        cards.append(
            f'<div class="card"><div class="top"><span class="hid">{hid}</span>'
            f'{_pill(v.get("verdict", "PENDING"))}</div>'
            f'<p class="claim">{claim}</p><div class="stats">{stats}</div></div>'
        )

    rob_rows = ""
    dom = robustness.get("domains", {})
    lat = robustness.get("latent", {})
    for hid in ("H2", "H4", "H7", "H8"):
        if hid in dom:
            rob_rows += (
                f'<tr><td class="h">{hid}</td><td>{_pill(dom.get(hid))}</td>'
                f"<td>{_pill(lat.get(hid))}</td></tr>"
            )

    figs = []
    for name, caption in _FIGS:
        path = figures_dir / name
        if not path.is_file():
            continue
        svg = path.read_text(encoding="utf-8")
        figs.append(
            f'<figure><div class="scroll">{svg}</div>'
            f"<figcaption><b>{html.escape(name)}</b> — {html.escape(caption)}</figcaption></figure>"
        )

    return (
        "<div class=\"wrap\">"
        '<p class="eyebrow">Chemotactic Task Allocation — research results</p>'
        "<h1>Decentralised task allocation, validated across generators</h1>"
        '<p class="thesis">Agents self-select work by a compatibility bid and a track-record '
        "correction, screened by a safety gate. Every verdict below is reproduced by one command "
        "and, for the population-dependent hypotheses, under a second, structurally different "
        "generator.</p>"
        f'<div class="tally"><span class="chip"><b>{supported}</b> of {total} hypotheses supported</span>'
        f'<span class="chip">{seeds} seeds</span>'
        f'<span class="chip">agents to {n_hi}</span>'
        '<span class="chip">deterministic, no external service</span></div>'
        '<h2>Hypotheses</h2>'
        f'<div class="grid">{"".join(cards)}</div>'
        + (
            '<h2>Generalisability — verdict by generator family</h2>'
            "<table><thead><tr><th>Hypothesis</th><th>Domains family</th>"
            f"<th>Latent family</th></tr></thead><tbody>{rob_rows}</tbody></table>"
            if rob_rows
            else ""
        )
        + '<h2>Figures</h2>'
        f'<div class="figs">{"".join(figs)}</div>'
        f"<footer>Generated by <b>cta dashboard</b> from results/summary.json. "
        f"Reproduce with <b>cta autorun --full</b>. Full protocol: {seeds} seeds, "
        f"agent counts to {n_hi}.</footer>"
        "</div>"
    )


def write_dashboard(results_dir: str | Path, out_path: str | Path) -> Path:
    results_dir = Path(results_dir)
    summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
    body = build_dashboard(summary, results_dir / "figures")
    page = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>CTA results dashboard</title>"
        f"<style>{_CSS}</style></head><body>{body}</body></html>"
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out
