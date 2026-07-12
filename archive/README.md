# Archive

Process and planning material that is not part of the two paper deliverables or
the reproducible research pipeline. Kept for provenance; nothing here is required
to build the papers, run the code, or reproduce the results.

## Contents

- `STATUS.md`: the running project status and "resume here" log used across
  development sessions. The living record of what is done and what comes next.
- `planning/`: forward-looking planning documents, superseded or realised by the
  work in `paper1/`, `paper2/`, and `src/`.
  - `roadmap.md`: the original phased research roadmap.
  - `strategy.md`: high-level strategy notes.
  - `publication_plan.md`: the unified-versus-split publication decision (resolved:
    split into Paper 1 and Paper 2).
  - `next_experiments.md`: a backlog of candidate experiments.
  - `harness_integration_plan.md`: the plan for folding harness-engineering
    framing into the papers (realised in both).
  - `paper2_plan.md`: the phased plan for Paper 2 (all phases now complete).
- `runbooks/`: operational runbooks.
  - `phase3_runbook.md`: the batched, resumable runbook for the real-agent
    (Phase 3) pilots.
- `paper2/` and `paper2.md`: the retired standalone second paper. Its strong parts
  (the head-to-head, the live ACP-broker vignette, and the harness framing) were
  merged into the main paper (`../paper1/`) as the deployment section, after a
  literature check found close prior work (MARGIN, UCCI). Kept here as the source
  the merged material came from.

## Where the live material lives

- Paper 1 (two editions): `../paper1/`. Markdown source: `../docs/paper.md`.
- Paper 2 (with the live-broker vignette): `../paper2/`. Markdown source:
  `../docs/paper2.md`.
- Shared library: `../src/cta/`. Experiment drivers: `../pilot_tasks/`. Outputs:
  `../results/`. Reference docs: `../docs/`.
