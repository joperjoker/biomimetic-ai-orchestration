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

## Staged batches, cheapest-and-most-valuable first

Order is chosen so the highest-value result lands first and the usage hog
(Opus) is last and smallest. "Weight" is relative subscription-usage load.

| # | Batch | Suite | Runs | Weight | Delivers |
|---|-------|-------|------|--------|----------|
| 1 | Build OOD overconfidence suite (in-session, no subagents) | new `pilot_tasks/ood_suite.py` | 0 | none | the tasks needed for batch 2 |
| 2 | Haiku OOD overconfidence tier | `ood_suite` | ~8-10 Haiku | low | **two-sided calibration curve** (reviewer #3): real overconfidence data on tasks beyond Haiku's competence |
| 3 | Ladder CIs, cheap cells | `expert_suite` | Haiku to n=8, Sonnet to n=6 | low-mid | tight CIs on the cheap ladder cells (reviewer #2) |
| 4 | Project CIs, cheap cells | `project_suite` | Haiku + Sonnet to n=3-5 | mid | CIs on project completion for the cheap cells |
| 5 | Held-out generalization suite (in-session build + Haiku/Sonnet runs) | new second expert suite | Haiku + Sonnet n=3 | low-mid | wrapper lift (H11) is not overfit to one 8-task set |
| 6 | Opus CIs (last, smallest) | `expert_suite` + `project_suite` | Opus to n=3 | high | frontier-cell CIs; keep n=3 to bound the Opus load |

Rule of thumb: batches 1-2 are the target for the **first** reset week (they
carry the single most valuable new result at low usage). Batches 3-5 fill
subsequent weeks. Batch 6 (Opus) is scheduled for a week with ample headroom.

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
