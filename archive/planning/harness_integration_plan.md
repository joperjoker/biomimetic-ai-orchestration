# Plan: fold harness-engineering elements into the CTA roadmap

Status: **Parts A, B, C done** (the free work). Part A (paper positioning) and
Part B (H13, SUPPORTED at full scale: completion 0.36 to 0.84 while raw stays
flat) are committed; Part C (ACP broker framed as a self-improving harness) is
folded into `docs/acp_integration.md`. Remaining is metered: the real-agent
self-improvement result batches with Phase 3/4 subagent runs.

## Context

Lilian Weng's "Harness Engineering for Self-Improvement" (Lil'Log, 2026-07-04)
argues near-term recursive self-improvement comes from the *harness* (the system
around a base model: planning loops, tools, memory, permissions, evaluation), and
its central bottleneck claim is that **self-improvement loops are only as good as
the signal they optimise -- the evaluator is the weak link.**

That is CTA's thesis one layer up: CTA's track-record correction (`R`, E4) plus
the integrity gate make a self-report-based evaluator *trustworthy*. So CTA is
naturally the calibration-robust signal/evaluation layer of a self-improving
harness, and its wrappers + ACP broker + gate are harness components.

Decisions taken: **additive positioning** (keep calibration-robust self-allocation
as the core thesis; add harness framing around it) and **add H13 self-improving
allocation, synthetic-first**.

Rejected as out of scope: the source report's "Part 2" suggestions (Firestore,
Vercel, Flutter, pedagogy) are off-topic; building full ACE / MCE / meta-harness
frameworks is too large -- cited as related work, not built. Stack stays
single-language Python with the existing SQLite `store.py`.

## Part A: paper concept -- additive harness positioning (free, writing only)

- `docs/paper.md`: add a short Related Work paragraph on harness engineering
  (Weng 2026; meta-harness; ACE; MCE) placing CTA as the *calibration-robust
  evaluation layer* a self-improving harness needs, citing the article's
  weak-evaluator bottleneck. Reposition existing pieces in harness vocabulary
  without changing the core claim: agent-wrapper = routing, track record / `store`
  = persistent memory, integrity gate = permission control, the ACP broker's
  route/observe/record cycle = the harness loop. Add H13 to the hypotheses table,
  Results, and Discussion.
- `docs/references.md` (and any bibliography the paper build reads): add the Weng
  2026 harness post and the meta-harness / ACE / MCE references. **Verify every
  citation online before adding, per the project reference rule.**
- Honest guardrail to state in the text: CTA is a *component* of a self-improving
  harness, not a full RSI system.

## Part B: results -- H13 self-improving allocation (synthetic-first, free)

Instantiate the article's "persistent memory + learn-from-failure loop" by making
the reliability table `R` persist and accumulate across sequential batches, and
measure that allocation quality rises with experience toward the oracle.

- `src/cta/engine.py`: thread a persistent reliability state through `run_batch`
  (extend the signature to accept/return an incoming `R` table if it does not
  already), reusing the existing `R` update logic. Determinism preserved via the
  existing seeded rngs.
- `src/cta/harness.py`: add `learning_curve(base, seeds, n_batches, ...)` that
  runs `n_batches` sequential batches carrying `R` forward, recording mean
  realised quality per batch under three arms: `reliability` (persistent memory,
  treatment), `raw` (memoryless control), and `true` (oracle reference). Reuse the
  existing sweep plumbing pattern (e.g. `calibration_sweep`).
- `src/cta/report.py`: add **H13 (self-improving allocation)** -- under
  `reliability`, mean quality increases with accumulated experience and the gap to
  the oracle shrinks. Supported when late-batch quality exceeds early-batch by a
  material margin (and/or a positive slope with a significant test), while `raw`
  stays flat.
- `src/cta/cli.py` (`autorun`): run `learning_curve`, emit
  `figures/learning_curve.svg` via the existing `line_chart` / `save_svg` in
  `src/cta/viz.py` (quality vs batch, one line per arm), add the block to
  `summary.json`, and pass it to `evaluate` and `write_results_md`.
- Real-agent version (deferred): the same persistent-`R` mechanism run over
  accumulated real-pilot outcomes, batched with Phase 3/4 metered runs. `store.py`
  (SQLite) is the durable backing for that path.

## Part C: product -- the ACP broker as a self-improving harness (folds into Phase 4)

- `docs/acp_integration.md`: add a "harness framing" subsection casting the broker
  as a harness exhibiting the article's three patterns -- (1) the plan/route/
  observe/record loop, (2) a first-class **persistent track-record store**
  (`store.py`) so the deployed router *self-improves across sessions* (the product
  embodiment of H13), (3) sub-agent/fleet management. Differentiator: not just a
  router, a self-improving calibration-robust harness. ACE / MCE / meta-harness
  are future inspiration, explicitly not built now.

## Sequencing against the existing roadmap

- **Phase 3** (real CIs + two-sided calibration) stays first -- committed,
  reviewer-driven, metered.
- **Part A** (paper positioning) and **Part B** (H13 synthetic) are free /
  low-usage and are good work for usage-constrained windows, slotting alongside
  Phase 3 writing and the Phase 4 ACP plumbing.
- **Part C** folds into **Phase 4** (ACP). The real-agent self-improvement result
  batches with Phase 3/4 metered runs.

## Critical files

- Paper/refs: `docs/paper.md`, `docs/references.md`.
- H13 code: `src/cta/engine.py`, `src/cta/harness.py`, `src/cta/report.py`,
  `src/cta/cli.py`, `src/cta/viz.py` (reuse `line_chart`/`save_svg`),
  `src/cta/store.py` (durable backing for the real path).
- Product: `docs/acp_integration.md`.
- Tests: the repo test dir.

## Verification

- `ruff check .` and `pytest` stay green. Add tests: `run_batch` carries `R`
  across calls deterministically; `learning_curve` shows quality rising under
  `reliability` and flat under `raw`, reproducible under a seeded rng; `autorun`
  writes `learning_curve.svg` and `summary.json` carries the H13 block and verdict.
- Re-run `cta autorun`; confirm H13 supported (quality rises with experience, gap
  to oracle shrinks) and refresh `results/` and the paper's Results.
- Rebuild the paper (`docs/build_report.py`) and confirm the harness related-work
  paragraph, H13 rows, and verified citations render.
- British English; no clause-separating dash; no puffery; determinism preserved.
