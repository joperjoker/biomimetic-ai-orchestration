# Paper 1 revision checklist (reviewer feedback)

Feedback received 2026-07-11 on the arXiv manuscript. Paper 1 (`paper1/`) is
otherwise frozen; these are the queued corrections to apply in a revision pass.
Each item is unchecked until done and verified in the rebuilt PDF.

> Note to reconcile: the feedback names the paper "Calibration-Robust Decentralised
> Task Allocation for Multi-Agent LLM Systems"; our `main.tex` title is
> "Decentralised Multi-Agent Task Allocation via Signal-Driven Selection". Confirm
> which title is intended before the revision (the feedback title foregrounds the
> calibration thesis and may be the better one).

> **Status note (checked against current `main.tex`, 2026-07-11).** The reviewer
> appears to have read an earlier version (their cited title also differs): three
> of the four prose items are already correct in the current LaTeX. Only the
> phrasing fix and the two figure fixes needed a change. Details per item below.

## 1. Text and equation corrections

- [x] **Eligibility typo (Sec 2.2):** ALREADY CORRECT. `main.tex` line 71 reads
  `\mathrm{elig}(a,t)=...`; there is no `lig(a,t)` anywhere in the source.
- [x] **Run-on after Activation/firing formula (Sec 2.2):** ALREADY CORRECT.
  `main.tex` line 74 already reads "with temperature $T\geq 0$; the deterministic
  threshold is the $T\to 0$ limit." (semicolon present).
- [x] **Redundant tilde (Sec 4):** ALREADY CORRECT. `main.tex` line 224 reads
  "completion falls to $\approx 0.37$" with no stray plain-text tilde; no
  double-approx exists in the source.
- [x] **Statistical phrasing (Sec 2.4):** FIXED. "a percentile bootstrap" ->
  "a bootstrap percentile interval" in `main.tex` and mirrored in `docs/paper.md`.

## 2. Diagram and table adjustments

- [x] **Chart axes (scaling figures):** FIXED. `src/cta/viz.py` `_fmt` now renders
  magnitudes >= 1000 as comma-separated integers (140,000) instead of `1.4e+05`.
  Affected figures (`cost_vs_n`, `scaling_peak_per_node`, `ladder_cost_fidelity`)
  regenerated; verified no `e+` notation remains.
- [x] **Unify metric (project figure, "Figure 7"):** FIXED. `pilot_tasks/project.py`
  now plots a module-completion fraction (0.0-1.0) with ylabel "module completion
  fraction", aligning with the completion-fraction figures.
- [x] **Anchor table (Sec 3.2):** ALREADY REFERENCED. `main.tex` line 174 cites the
  robustness table inline: "The verdicts are the same under both families
  (Table~\ref{tab:robust})." If a stronger closing anchor is wanted in the
  revision, append the reviewer's suggested sentence at the end of the subsection.

## 3. Writing style (optional, keep the rigour)

- [ ] **Sentence structure:** break long multi-clause sentences, especially in the
  Abstract and Section 1, so concepts (activation barriers, Rejection Gates) can
  be read independently.
- [ ] **Active voice:** prefer active voice when describing the task and agent
  wrapper mechanics, to clarify operational roles.
- [ ] **Thematic grounding:** reconnect each technical explanation to the primary
  objective, relieving the scaling bottleneck of centralised orchestrators.

## Where these live

- Equations/prose/table anchor: `paper1/main.tex` (and mirror in `docs/paper.md`).
- Figure axis formatting: `src/cta/viz.py` tick/label rendering; regenerate the
  SVGs, then re-export the figure PDFs (`paper1/README.md` cairosvg snippet).
- After edits: rebuild via `paper1/build.sh`, run `python -m pytest -q` and
  `ruff check .`, confirm the forbidden-dash check passes on any `.md` changes,
  then commit. British English; no clause-separating dash in `.md`.
