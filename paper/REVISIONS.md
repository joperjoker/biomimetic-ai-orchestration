# Paper 1 revision checklist (reviewer feedback)

Feedback received 2026-07-11 on the arXiv manuscript. Paper 1 (`paper/`) is
otherwise frozen; these are the queued corrections to apply in a revision pass.
Each item is unchecked until done and verified in the rebuilt PDF.

> Note to reconcile: the feedback names the paper "Calibration-Robust Decentralised
> Task Allocation for Multi-Agent LLM Systems"; our `main.tex` title is
> "Decentralised Multi-Agent Task Allocation via Signal-Driven Selection". Confirm
> which title is intended before the revision (the feedback title foregrounds the
> calibration thesis and may be the better one).

## 1. Text and equation corrections

- [ ] **Eligibility typo (Sec 2.2):** `$lig(a,t)=1...$` -> `$elig(a,t)=1...$` to
  match the subsequent definition.
- [ ] **Run-on after Activation/firing formula (Sec 2.2):** insert a semicolon or
  period before "the deterministic threshold", separating the temperature
  definition from the limit definition.
- [ ] **Redundant tilde (Sec 4):** `to`≈` $\approx0.37$` -> `to $\approx0.37$`
  (drop the plain-text tilde, keep the LaTeX approximation).
- [ ] **Statistical phrasing (Sec 2.4):** "a percentile bootstrap" -> "a bootstrap
  percentile interval" (or "bootstrap confidence intervals") to match the
  terminology used elsewhere.

## 2. Diagram and table adjustments

- [ ] **Chart axes (Figures 1 and 6):** remove programming-style scientific
  notation (e.g. `1.4e+05`); use comma-separated numbers (140,000) or
  `$1.4 \times 10^5$`. Fix in the axis formatter in `src/cta/viz.py` (tick
  labelling) and regenerate the figures.
- [ ] **Unify metric (Figure 7):** plot the y-axis as a completion fraction
  (0.0-1.0) rather than a raw count of modules, to align with Figures 2, 5, 6.
  Update the project figure generation.
- [ ] **Anchor orphaned table (Sec 3.2):** add a closing sentence referencing
  Table 3, e.g. "The detailed verdicts comparing the outcomes under both the
  domains family and the latent family are summarised in Table 3."

## 3. Writing style (optional, keep the rigour)

- [ ] **Sentence structure:** break long multi-clause sentences, especially in the
  Abstract and Section 1, so concepts (activation barriers, Rejection Gates) can
  be read independently.
- [ ] **Active voice:** prefer active voice when describing the task and agent
  wrapper mechanics, to clarify operational roles.
- [ ] **Thematic grounding:** reconnect each technical explanation to the primary
  objective, relieving the scaling bottleneck of centralised orchestrators.

## Where these live

- Equations/prose/table anchor: `paper/main.tex` (and mirror in `docs/paper.md`).
- Figure axis formatting: `src/cta/viz.py` tick/label rendering; regenerate the
  SVGs, then re-export the figure PDFs (`paper/README.md` cairosvg snippet).
- After edits: rebuild via `paper/build.sh`, run `python -m pytest -q` and
  `ruff check .`, confirm the forbidden-dash check passes on any `.md` changes,
  then commit. British English; no clause-separating dash in `.md`.
