# Paper 2 plan: the deployed calibration-robust harness (Path 2)

Paper 1 (`paper/`) is submitted and frozen: the mechanism (CTA) and the evidence
it works. Paper 2 is the continuation, a separate paper: CTA **deployed** as an
Agent Client Protocol (ACP) broker that self-improves in service, with a
**head-to-head** against the routers a top-tier reviewer asks for.

Thesis: a calibration-robust router that corrects self-reported confidence by a
persistent track record beats naive-self-report routing on cost at equal
completion, and approaches always-frontier completion at a fraction of the cost,
measured live on real agents through a real protocol.

## Phasing for pause/resume

Every phase ends with tests green, `ruff` clean, committed and pushed, and the
STATUS resume pointer updated, so any phase boundary is a safe stop. Only Phase 2C
spends subagent budget; the rest is free plumbing that completes regardless of
usage. Phase 2C writes idempotent on-disk cells and resumes by re-running (it
skips cells already present), so a mid-run usage cutoff loses nothing.

### Phase 2A (free): broker hardening

Extend `src/cta/acp.py` so the broker carries the paper's mechanism live:

- **Elicitation, pluggable.** `Bidder` seam with two modes: `prior_bidder`
  (bid from a per-tier prior + track record, no probe; the current default) and
  `probe_bidder(probe)` (send each candidate a confidence probe, parse a bid in
  [0,1]; one cheap extra turn per candidate).
- **Integrity gate.** `clamp_gate` (and the `Gate` seam) sanitises raw bids before
  the track-record correction, the live form of the paper's gate.
- **Multi-downstream.** `make_fleet_downstream(mapping, default)` routes each model
  name to its own solver, so the fleet can be heterogeneous downstreams.

Tests: probe-mode bids, gate clamping, per-model downstream dispatch. Free.

### Phase 2B (free): head-to-head evaluation harness

New `src/cta/headtohead.py`: run a task suite through four routing policies with a
**pluggable solver** (a deterministic simulated solver for tests; the real
subagent solver swaps in for 2C):

1. `cta_corrected` -- `wrappers.route` with the accumulating track record.
2. `naive_self_report` -- route on raw bids only (reliability pinned to 1.0).
3. `always_frontier` -- always the most capable model.
4. `single_cheapest` -- always the cheapest model.

Report per policy: completion, blended dollar/token cost, and the probe overhead
(extra turns) the elicitation costs. Bootstrap CIs via `cta.stats`; figures via
`cta.viz`. A markdown/JSON writer. Tests assert the policies separate as designed
on the simulated solver (naive over-routes to cheap-but-unreliable; corrected
matches frontier completion below frontier cost). Free.

### Phase 2C (metered, batched): run the head-to-head on real subagents

Driver `pilot_tasks/headtohead.py` over the existing expert/project suites. Each
cell is one `(policy, task, replicate)` solve, written to
`results/headtohead/{policy}__{task}__{k}.txt` in the same submission format as
the ladder tier, scored against hidden tests. The driver skips any cell already on
disk, so it is fully resumable across sessions. Orchestrated by spawning
`Agent(model=...)` subagents one-shot, no tools, as in Phase 3. Batch small;
commit partial results; pause when usage is spent; resume next session.

Then analyse -> figures -> the head-to-head numbers with CIs.

### Phase 2D (free): Paper 2 draft

New `paper2/` (leave `paper/` untouched): "ACP-native calibration-robust routing".
Intro (the deployed-harness thesis, Weng 2026 framing), the broker architecture,
the head-to-head result table + figures, the probe-overhead cost accounting, and
an honest limitations section (protocol youth, probe cost, Claude-underconfidence
bound carried from Paper 1). Draft first in `docs/paper2.md`, then LaTeX.

## Guardrails

- British English; no clause-separating dash in `.md` (CI-checked); no puffery;
  determinism preserved; `paper/` stays frozen.
- Verify every new citation online before adding it.
- Honest bound already known: Claude self-reports are *underconfident* on standard
  tasks, so the "overconfident-arm" head-to-head advantage is failure-contingent;
  state it, do not manufacture it with gotcha tasks.
