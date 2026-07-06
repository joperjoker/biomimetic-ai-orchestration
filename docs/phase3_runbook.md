# Phase 3 runbook: subscription-only real-agent hardening

This is the execution plan for the remaining real-agent evidence (reviewer
round-2 asks), designed to run **entirely on a Claude Pro subscription with no
API key**, staged across weekly usage resets. It is a checklist, not code to
run now: it exists so the work survives a pause and reset-week is turnkey.

## The one insight that makes this free of dollars

The real-agent pilots (ladder, project, hard tier) are executed by **Claude Code
subagents spawned inside the session**. Those subagents draw on the session's
Claude subscription usage, not an API key. So the whole pipeline runs at zero
dollar cost; the only constraint is the **weekly usage cap**. The "~$50" figure
in planning was an illustrative API-list-price equivalent, not a bill.

Consequence: this is a **scheduling** problem, not a feasibility one. Usage
resets weekly, every batch is committed, and the analysers recompute
deterministically from committed submissions, so the run resumes cleanly across
resets and sessions.

## Frugal design principles (minimise usage per unit of evidence)

1. **Haiku-first.** Put replicate volume on Haiku; it is by far the lightest on
   the allowance. The most valuable new result (the two-sided calibration curve)
   is *best* done on Haiku anyway, because Haiku is where real overconfidence
   shows up.
2. **Minimal Opus.** Opus subagents are the usage hog. Reserve Opus for the CI
   cells that genuinely need the frontier model, at n=3, not n=5.
3. **Batch per subagent.** One subagent solves the whole suite in a run, not one
   subagent per task. Fewer, fuller runs mean less orchestration overhead.
4. **Free work in-session.** Scoring, figures, the paper build and the dashboard
   are stdlib Python at trivial cost. Do all analysis and writing in-session;
   spend the allowance only on the subagent *solve* calls.
5. **Commit after every batch.** So a mid-week cap or a session restart never
   loses a completed batch, and the next reset resumes where it stopped.

## The statistical insight: real CIs live on the cheap models

Reviewer #2 wants confidence intervals, but a CI is only informative where there
is variance. Map the variance before spending any usage:

- **Variance-carrying cells (need replicates):** the Haiku ladder cells (Haiku
  bare 0.925, and the Haiku wrapped lift) and every OOD calibration cell. These
  are all Haiku, the lightest model on the allowance, so replication is cheap.
- **Saturated cells (ceiling/floor, low variance):** Sonnet and Opus completion
  sit at 1.00, and the bare project sits at 0. A bootstrap on all-identical
  outcomes is degenerate; the honest interval is the binomial / rule-of-three
  interval, which is a function of n, not of piling on runs beyond a modest n.
  Three runs pin these down, so Opus does **not** need heavy replication to earn
  a CI.

The variance is Haiku-concentrated. We nevertheless adopt a **balanced design**
(equal n across the three models on the ladder and the OOD tier): it removes the
"why is Opus under-powered?" question, and the extra runs on the saturated
Sonnet/Opus cells genuinely tighten their intervals (rule-of-three lower bound
rises from about 0.37 at n=3 to about 0.74 at n=10). This over-samples the
low-variance cells, which is statistically inefficient but the point is a
defensible, balanced table; the conclusions are unchanged (Haiku still carries
the real variance, the two-sided curve still comes from the OOD tier). The Opus
tail is therefore larger than a variance-weighted plan, and is paced across
sessions accordingly.

## Run budget for the two deliverables (balanced design, additive over what exists)

Existing: ladder Haiku bare n=5, Haiku wrapped n=2, others n=1; project n=1 per cell.

**1. Real confidence intervals (reviewer #2)** -- equal n across models.

| Cell group | Target n | Add | of which Opus |
|------------|----------|-----|---------------|
| Ladder, 6 cells (3 models x 2 conditions) | 10 | +49 | +18 |
| Project, 6 cells | 5 (near-deterministic 0/1, converges fast) | +24 | +8 |

**2. Two-sided calibration curve (reviewer #3)** -- equal n across models so the
three reliability diagrams overlay with comparable confidence.

| Cell | Target n | Add | of which Opus |
|------|----------|-----|---------------|
| OOD suite, Haiku / Sonnet / Opus | 10 each | +30 | +10 |

**Totals: ~31 Haiku, ~36 Sonnet, ~36 Opus (~103 runs).** Balanced. The Opus tail
(~36 runs) is the pacing item; it is spread 2-3 per session across weekly resets.

Optional stretch (not required by either reviewer, defer): a held-out second
expert suite at n=10 to show the wrapper lift is not overfit to one 8-task set.

## Fitting the Pro session limit

The Pro plan caps usage per rolling session and per week, and every subagent
solve draws on it. The design fits by construction:

- **Micro-batch per session.** Run about 3-5 subagent solves per session (mostly
  Haiku/Sonnet), commit, let the session limit reset, continue. A capped-out
  session never costs rework because the prior batch is committed.
- **Value first.** The first session of reset-week builds the OOD suite
  (in-session, no solves) and runs the Haiku OOD batch, landing the two-sided
  curve. Then trickle the Haiku/Sonnet CI replicates over following sessions.
- **Cluster the Opus tail.** The ~36 Opus runs are the pacing item; put 2-3 into
  each session that has clear weekly headroom.
- **Resume across resets.** `python -m pilot_tasks.analyse` and
  `cta.cli reproduce-all` recompute everything from committed data, so the paper
  refreshes batch by batch and the run survives any number of resets.

At about 3-5 solves per session, the ~103-run balanced design spans roughly
20-35 sessions across however many weekly resets the Opus tail requires. Exact
fit depends on the absolute Pro limits, which the session cannot read; but
because it is micro-batched and fully resumable, the total count only changes how
many sessions it spans, never whether it completes. Nothing here needs an API
key.

## What is prebuilt vs pending

- **Prebuilt (reused as-is):** `expert_suite.py`, `project_suite.py`, the
  ladder/project runners and analysers (`ladder.py`, `project.py`,
  `analyse.py`, `score_submissions.py`), the figure and dashboard build, the
  paper build (`docs/build_report.py`).
- **Pending (build in-session at the start of reset-week, no subagent cost):**
  `pilot_tasks/ood_suite.py` (hard, trap-dense tasks beyond a weak model's
  competence, references hard-checked against canonical outputs), and a second
  held-out expert suite for batch 5.

## Reproduce the free parts any time (no subagents, no usage)

```
python -m pilot_tasks.analyse         # scores + reliability diagram from committed submissions
python -m cta.cli reproduce-all       # all synthetic results, figures, dataset
python docs/build_report.py --pdf /opt/pw-browsers/chromium-1194/chrome-linux/chrome
```

## Merging new runs into the paper

After each batch of subagent runs: commit the new submissions, re-run the
relevant analyser to refresh figures and summaries, update the affected paper
paragraphs and CI values, regenerate `docs/research.html` and `docs/paper.pdf`,
run `ruff check .` and `pytest`, then commit. The verdict tables and CIs update
from the committed data, so the paper stays in sync batch by batch.
