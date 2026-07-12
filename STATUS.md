# Project Status

A running log of what is complete and what comes next. Read this, then `claude.md`, `docs/next_experiments.md`, and `docs/measures.md` to resume in a fresh session.

## Two-paper split (recorded 2026-07-11)

**Paper 1 is being submitted now.** The arXiv package in `paper/` (author Teo Qing
Cong Eugene, Independent) is the submission: `main.tex` + `refs.bib` + `main.bbl`
+ `figures/`, primary category cs.MA. This is Paper 1, the calibration-robust
decentralised task-allocation result (CTA, H1-H13, the ladder/project/held-out/OOD
real-agent tiers, the synthetic protocol). It is frozen for submission; do not
add new results to `paper/main.tex`. Corrections/rebuttal edits only.

**Paper 2 is the continuation.** Ongoing research (Path 2 below) is now explicitly
scoped as a *second, separate paper*, not an update to Paper 1. Its thesis is the
deployed self-improving CTA harness: the ACP broker as a calibration-robust router,
the SOTA benchmark head-to-head (CTA's calibrated router vs a naive static-capability
router vs single-frontier), and the real-agent self-improvement result (H13 over a
persistent store across sessions). Start a fresh paper source (e.g. `paper2/`) when
the results are in; keep `paper/` untouched. Read `docs/publication_plan.md` for the
framing. Before continuing Path 2, note: Paper 1 = the mechanism + evidence it works;
Paper 2 = the deployed harness + the competitive head-to-head.

**Paper 2 is phased for pause/resume (`docs/paper2_plan.md`).**
- **Phase 2A (free): DONE.** Broker hardening in `src/cta/acp.py`: pluggable
  elicitation (`prior_bidder` default, `probe_bidder(probe)` = one probe turn per
  candidate), integrity `clamp_gate`, and `make_fleet_downstream` multi-downstream
  dispatch. `tests/test_acp.py` +5 (148 pass, ruff clean).
- **Phase 2B (free): DONE.** `src/cta/headtohead.py`: four routing policies
  (`cta_corrected` / `naive_self_report` / `always_frontier` / `single_cheapest`)
  over a task stream with a pluggable `Solver`; completion (bootstrap CI) + cost +
  probe-overhead metrics; `completion_cost_figure` + `write_report`
  (summary.json/RESULTS.md/headtohead.svg). `tests/test_headtohead.py` +7 (155
  pass, ruff clean). Sim sanity: cta 1.00 completion at 1.51x frontier cost saving,
  +0.50 over naive, probe overhead 23%. Real numbers come from 2C.
- **Phase 2C (real agents): DONE, zero new metered cost.** The head-to-head is a
  routing question over outcomes the Phase 3 ladder already collected, so
  `pilot_tasks/headtohead.py` answers it as a **leave-one-replicate-out replay**:
  reliability and self-reports estimated from the training replicates, each policy
  scored on the held-out replicate it did not see. Real result on the expert
  `bare` tier (10 folds): CTA-corrected **0.988 [0.963, 1.000]** completion at
  **25.3x** cost saving vs always-frontier (1.000), beating naive self-report /
  single-cheapest (both **0.950**) by **+0.037**. Finding: with uniformly
  (over/under)confident Claude self-reports, naive routing *collapses to
  always-cheapest* (raw bids always clear the barrier), so the track-record
  correction is what creates the differentiation. `results/headtohead/`
  (summary.json, RESULTS.md, headtohead.svg) + `results/figures/headtohead.svg`.
  `tests/test_headtohead_replay.py` +4 (159 pass, ruff clean). The optional live
  end-to-end broker demo over a real subagent solver remains available if we later
  want a deployment vignette; the headline result is banked without it.
- **Phase 2D (free): LaTeX package built.** `paper2/` created: `main.tex`
  (title "Calibration-Robust Routing as a Self-Improving Agent Harness"), `refs.bib`
  (Paper 1's entries + verified ACP spec citation, Zed Industries 2025, + a Paper 1
  companion entry), `figures/headtohead.pdf`, `build.sh`, `README.md`. Builds clean
  (5 pages, all citations resolved). Ported from `docs/paper2.md`; carries the real
  head-to-head table (CTA 0.988 [0.963, 1.000] at 25.3x saving) and figure. Paper 1
  (`paper/`) stays frozen. Remaining before submission: a proofread and the optional
  live-broker vignette.
- **Phase 2D source draft (free): DONE.** `docs/paper2.md` written: abstract, intro
  (deployed-harness thesis, Weng 2026), related work (FrugalGPT/RouteLLM/ACP), the
  broker architecture, the head-to-head method + result table + the
  naive-collapses-to-cheapest finding, probe-overhead accounting, honest
  limitations, conclusion. Next: verify citations online, then port to `paper2/`
  LaTeX (reuse `paper/refs.bib` + the head-to-head figure). `paper/` stays frozen.

**Path 2 status: 2A-2C complete and 2D drafted, all at zero metered subagent
cost** (2C ran as a leave-one-out replay over Phase 3's banked outcomes). Optional
remaining: a live end-to-end broker vignette over a real subagent solver (metered,
deployment colour only), and the `paper2/` LaTeX build. To resume, say "finish
Paper 2" (LaTeX) or "run the live broker demo" (metered).

## Paused 2026-07-11 (low usage)

**Paper 1 has reviewer feedback: see `paper/REVISIONS.md`** (a full checklist of
equation/prose fixes in Secs 2.2/2.4/4, figure fixes for Figs 1/6/7, a Table 3
anchor in Sec 3.2, and optional style edits). Paper 1 stays frozen except for this
revision pass. One open question logged there: the feedback's title
("Calibration-Robust Decentralised Task Allocation for Multi-Agent LLM Systems")
differs from `main.tex`'s current title; confirm which to use.

**Path 2 / Paper 2 is paused mid-stream, all phases at a clean stop:** 2A-2C are
DONE and committed (broker hardening, head-to-head harness, the real-agent
leave-one-out replay: CTA 0.988 completion at 25.3x cost saving), and 2D is DRAFTED
in `docs/paper2.md`. Nothing is in flight; 159 tests pass, ruff clean, tree pushed.
To resume Paper 2: "finish Paper 2" (port `docs/paper2.md` to `paper2/` LaTeX) or
"run the live broker demo" (the only metered piece, optional colour). To resume
Paper 1: "apply the revisions" (work `paper/REVISIONS.md`).

## Resume here (next session)

**Where things stand.** Branch `claude/biomimetic-ai-orchestration-init-0nb5db`.
143 tests pass, `ruff` clean, tree clean and pushed. Phase 3 (real-agent
hardening) is complete; Path 1 (the TMLR-ready pass) is done and Paper 1 is
submission-ready and being submitted now (`paper/` LaTeX package; `docs/paper.pdf`
also built); Path 2 (the ACP broker, now scoped as Paper 2) is started, with the
skeleton P4.0-P4.2 built and tested (`src/cta/acp.py`). Read
`docs/publication_plan.md` first for the unified-vs-split decision (now resolved:
split).

**Paused here (resume next session).** The next action is the metered Path 2
differentiator: P4.3 (wire the broker's `downstream` to a real subagent solver),
then P4.6 (the SOTA benchmark head-to-head -- CTA's calibrated router vs a naive
static-capability router vs single-frontier). Nothing is in flight; no background
work. To resume, say "continue Path 2".

**Phase 3 done: the balanced-n real-agent CI plan is complete.**
- **Capability ladder** (`results/live_pilot/ladder/`, `pilot_tasks/ladder.py`):
  all six cells at n~10 with bootstrap CIs. Haiku bare 0.950 [0.90, 0.988],
  wrapped 0.986 [0.958, 1.00]; Sonnet 0.988 -> 1.00; Opus 1.00. Task-wrapper lift
  +0.036 (Haiku); agent-wrapper routing ~47x cheaper (wrapped) / ~50x (bare).
- **Project** (`results/live_pilot/project/`, `pilot_tasks/project.py`): all six
  cells at n=5. Bare fails (completion 0) and wrapped delivers (1.00) for every
  model in every replicate; cross-model wrapped assembly ~39x cheaper.
- **Held-out generalisation** (`pilot_tasks/held_out_suite.py`, `held_out.py`): a
  second independent 8-task tier; Haiku+Sonnet n=3 x bare/wrapped both saturate
  (lift 0.00). Honest bound: the wrapper lift is failure-contingent, a no-op with
  no regression where the model is already reliable.
- **OOD calibration** (`pilot_tasks/ood_suite.py`, `ood.py`): Haiku is
  underconfident even out of distribution (gap -0.105). The two-sided curve's
  overconfident arm is not sourceable from Claude on standard tasks; not
  manufactured with gotcha tasks. This is the one open scientific gap.

**Also landed this session.**
- **H13 self-improving allocation** (`cta.harness.learning_curve`, report H13
  SUPPORTED): a persistent, accumulating track record lifts completion 0.36 ->
  0.84 toward the oracle; memoryless raw stays flat.
- **Harness-engineering positioning** (Weng 2026) folded into paper section 6 and
  contributions; CTA framed as the calibration-robust signal layer of a
  self-improving harness (component, not a full RSI system).
- **ACP integration plan** (`docs/acp_integration.md`): CTA as an ACP broker;
  mostly-free plumbing, the vehicle for the SOTA head-to-head.

**What is next.** Decision pending: unified -> TMLR vs split-and-aim-top-tier
(`docs/publication_plan.md`).

- **Path 1 (TMLR-ready pass): DONE.** Held-out generalisation bound
  (`held_out_suite.py`), powered CIs throughout, verified related-work vs
  FrugalGPT (Chen, Zaharia, and Zou, 2023) and RouteLLM (Ong et al., 2024), and
  `docs/paper.pdf` built. Only venue-specific LaTeX formatting remains (needs a
  target template).
- **Path 2 (top-tier lever): STARTED.** The ACP broker skeleton is built and
  tested (`src/cta/acp.py`, `tests/test_acp.py`; P4.0-P4.2 done). Remaining:
  1. **P4.3 real downstream** -- wire the broker's `downstream` callback to a real
     solver (a subagent that solves a task and returns pass/fail).
  2. **P4.6 the SOTA benchmark head-to-head (metered, the differentiator):** CTA's
     calibrated router vs a naive static-capability router vs single-frontier, on
     an established benchmark (HumanEval+/MBPP+ subset) or the three in-repo suites
     as a controlled stand-in. Report completion, cost, and the confidence-probe
     overhead. Then decide upgrade-in-place vs split.
- **Optional science:** the live competing-swarm allocation over the concurrent
  store; a harder OOD tier for the overconfident arm (treat cautiously to avoid
  the gotcha critique).

**Operational notes.** Reproduce synthetic results with `cta reproduce-all`; the
real-agent tiers with `python -m pilot_tasks.ladder`, `... project`, `... held_out`,
`... ood`, `... analyse`. Rebuild the paper with `python docs/build_report.py`
(add `--pdf /opt/pw-browsers/chromium-1194/chrome-linux/chrome` for the PDF).
Roadmap docs: `docs/publication_plan.md`, `docs/phase3_runbook.md`,
`docs/harness_integration_plan.md`, `docs/acp_integration.md`.


## In one line

Chemotactic Task Allocation (CTA): decentralised, signal-driven orchestration of a swarm of coding agents, where a task wrapper scores an agent's role, skills, and prompt into a compatibility, an agent takes a task only when its compatibility reaches the task's activation energy, and a trust gate screens the winner before write access. This is AI coding-agent orchestration research; the biology is design inspiration only.

## North Star

The one claim under test: decentralised, signal-driven self-selection relieves the central-orchestrator bottleneck while holding match quality and safety. Sharpened after a literature comparison (decentralised self-selection is well covered): the contribution is calibration robustness. Self-assessment miscalibration is the failure mode of self-selection (the compatibility bid is the agent's own self-report, E13), and a track-record correction (the reliability R, E4) recovers the completion that miscalibration costs, with the integrity gate as a safety backstop. Motivated by MarketBench (Fradkin and Krishnan, 2026). Every addition serves that claim or is marked a consideration.

## Decisions locked

- Framing: AI coding-agent orchestration; biology as inspiration, not subject.
- Platform: self-contained, minimal. SQLite in WAL mode (transactional atomic claim) is the coordination store; an optional Postgres adapter exists. No external service in the default path.
- The task wrapper computes compatibility `c` from role, skills, and prompt via measurable sub-scores; activation is on compatibility (`c >= Ea`); the Binding Energy `B = c x C_tilde / L` ranks the willing agents only.
- Two stages run in order: Stage 1 deterministic simulation swarm, then Stage 2 the LLM stage (required, Claude Code agents).
- Scaling sweep to ten thousand agents (fitted growth exponent, via a central load-only fast path). Licence Apache-2.0. Language Python 3.11+.

## Latest state

Current hypothesis verdicts from `cta reproduce-all` (127 tests pass, `ruff` clean): H1 (scaling), H3, H4 (safety), H5, H7, H8, H9, and H10 supported; H2 and H6 not supported against the full-information optimum and reported honestly. Two further hypotheses, H11 (task-wrapper lift) and H12 (agent-wrapper cost-efficiency), are confirmed on real Claude agents across three model families and reported with their small-sample caveat (see the resume block and `docs/paper.md`). H9 is the fair coordination result against an information-bounded central baseline; H10 shows the activation barrier routes each subtask of a heterogeneous job to a correct specialist (accuracy 1.00 with the barrier, 0.47 without under tight observability). Evidence added recently: the bounded baseline, fitted scaling to ten thousand agents, bootstrap confidence intervals and power notes, the released dataset CSV, the biomimicry ablation, the token and dollar cost model, one-command reproduction, and the specialist-routing study (H10, which gave the barrier the quality role the batch ablation lacked). Phase 2 of the plan is essentially complete: added the latency-quality Pareto dial (P2.2), the runnable product PoC (`examples/poc`, P2.6), and calibration grounded in the measured MarketBench mixture (P2.1, H8 recovery about 0.48 there). Also added P3.2 (a strategic adversary demoted by the track record over rounds, first-round win share about 0.22 decaying to zero). All non-budget Phase 3 items are now done too: P3.3 streaming arrival, and P3.1 concurrent multi-process claiming (the atomic claim validated under real OS-level contention). P2.5 and P3.4 are now done (the two-family live pilot, the capability ladder, and the dependency-graph project), the wrapper layer is extracted as a product, and the paper carries an executive summary, embedded figures, a wrapper-build section, an outlook, and a conclusion. The remaining work is the publication track and deeper real-agent power. 127 tests pass.

## Completed

- Specification and foundation (Phase 0): `README.md`, `claude.md` (master context and eight-persona consortium), `docs/paper.md` (introduction, methodology, formal framework E1 to E14, RQ1 to RQ6, H1 to H6), `docs/theory.md`, `docs/architecture.md`, `docs/measures.md` (operational definitions), `docs/roadmap.md`, `docs/glossary.md`.
- Project hygiene: `LICENSE` (Apache-2.0), `.gitignore`, `CONTRIBUTING.md`, `CHANGELOG.md`, CI workflow, `pyproject.toml` (packaged, `src` layout).
- References verified online (nine references, DOIs added).
- Consistency passes: notation (`c`, `C_tilde`, coordinator work), Recursive Language Models naming, activation on compatibility, platform text, all reconciled and guarded by tests.
- Code, Phase A: `src/cta/scoring.py`, the measurable model E1 to E11 as pure functions (compatibility, eligibility, reliability, effective capability, Binding Energy, activation and firing, tie breaker, winner selection, gate). Twenty-one unit tests in `tests/test_scoring.py`.
- Code, Phase B: `src/cta/store.py`, the self-contained SQLite store (WAL mode) with the transactional atomic claim, the four tables (tasks, agents, events, attempts), event append, attempt recording, and a reliability read. A concurrency test in `tests/test_store_atomic.py` confirms that among 32 contending claimers exactly one wins.
- Direction A applied (scaling fix): added peak-per-node and total-work metrics (A1) and bounded observability, each agent samples `k` tasks (A2). H1 is now decisively supported: CTA peak per-node load stays flat at about 32 while the central scheduler grows about 64 times over the swept range. The earlier marginal H1 was a measurement-and-mechanism artefact. H4 and H6 remain not supported and are the next targets.
- All six hypotheses are now evaluated by `cta autorun` (H3 feasibility labelling, H4 gate ablation under injected unreliability, and H5 stability across the `Ea` by `T` grid were added). At demo scale H1, H2, H3, and H5 are supported and H4 and H6 are not supported; the paper's Results and Discussion (sections 3 and 4) record these faithfully, including the negative results (marginal scaling advantage under high contention, and the gate being partly redundant with reliability-coupled selection). A compatibility bug (the sub-score floor inflated perfect matches) was found and fixed.
- Code, Phase K (deterministic Stage 2): `src/cta/autoresearch/` (`search_space.py` and `loop.py`), the propose, evaluate, keep-or-revert loop that tunes the bounded search space (activation energy and temperature) to improve a protected metric under a guardrail, with a decision ledger. It runs with no model calls; an LLM proposer can be substituted without changing the loop. `src/cta/pilot.py` defines the live-pilot interface (opt-in, not executed). `REPRODUCE.md` and a CI autorun smoke are in place.
- Code, Phases H, I, and J: `src/cta/viz.py` (pure-SVG line charts, zero dependencies), `src/cta/report.py` (hypothesis verdicts H1 to H6 and a Results Markdown writer), and `src/cta/cli.py` (`cta autorun`, the one-command autonomous run). Registered as the `cta` console script. Running `cta autorun` produces `results/summary.json`, `results/RESULTS.md`, and SVG figures. At demo scale H1 and H2 are supported, H6 is not supported (reported faithfully), and H3 to H5 are pending the concurrent engine and further sweeps. This is the "start"-ready milestone.
- Code, Phases F and G: `src/cta/stats.py` (confidence intervals, Mann-Whitney U with tie correction via `statistics.NormalDist`, Cliff's delta, Holm-Bonferroni) and `src/cta/harness.py` (the four conditions run across seeds, with a scaling sweep and a heterogeneity sweep, and aggregation to mean and 95 per cent confidence interval). Tests in `tests/test_analysis.py`. Pure standard library.
- Code, Phases C to E (in-process): `src/cta/quality.py` (ground-truth Q, E12), `src/cta/generators.py` (seeded agent and task populations with the heterogeneity control), `src/cta/engine.py` (the fast event-loop `run_batch` for the decentralised conditions `cta` and `pull_based`, returning per-task outcomes and a summary), and `src/cta/baselines.py` (central greedy and optimal assignment, with the optimal using scipy when available or a brute-force optimum for small instances). Tests in `tests/test_sim.py`. All 33 tests pass; `ruff` clean. An end-to-end smoke over 200 agents and 150 tasks runs and shows the expected shape (CTA matches pull-based quality at much lower coordinator work, and beats central greedy on mean quality).
- Repositioning around calibration robustness (after a literature comparison): the engine now separates the agent's self-reported compatibility `c_hat` (E13, drives firing and the bid) from the true compatibility (drives realised quality), with a `selection_mode` of `raw` (self-report only), `reliability` (self-report discounted by the track record R), or `true` (full-information oracle). Added `src/cta/harness.py::calibration_sweep` and `safety_ablation`, the `with_miscalibration`, `with_track_record`, `with_capability_spread`, and `with_injected_adversarial` generators, and the `overconfidence_gap`, `completion_rate`, and `integrity_violations` measures. Two new hypotheses: H7 (self-reports over-predict realised success, the failure mode) and H8 (the track-record correction recovers completion, from about 0.37 to about 0.87, p about 0.009). References MarketBench (Fradkin and Krishnan, 2026, arXiv:2604.23897) and the confidence-calibration collaboration paper (Zhang et al., 2026, arXiv:2603.03752), both verified.
- Rigour pass and temporal engine (after critical review): the Rejection Gate is now an imperfect detector (`GateConfig.scope_recall`), so H4 is a measured reduction (about 83 per cent at recall 0.9), not a tautological zero. H7 no longer claims the overconfidence gap grows with the injected bias; it is reported as the structural fit-versus-competence gap. New `src/cta/temporal.py`, a round-based engine with agents that hold work over time, task stalls, activation-energy annealing (E14), and per-task latency and stall, so allocation latency, throughput, starvation, and annealing become real measured quantities. H5 is now tested by the temporal engine via `harness.annealing_curve`: without annealing feasible tasks are never claimed (unmet 1.0, stall at the horizon), with a positive rate every feasible task resolves at bounded stall (1 to 3 rounds), and the maximum stall falls smoothly as the rate rises. `harness.temporal_metrics` reports latency and throughput on the base population; `cta autorun` adds the `annealing_stall.svg` figure and the `annealing` and `temporal` blocks to `summary.json`. At demo scale H1 to H5, H7, H8 are supported and only H6 is not. Sixty tests pass; `ruff` clean.

- Tier 1 rigour and full run: applied the Holm-Bonferroni correction the paper promised (H2, H8 corrected, H8 verdict rests on the corrected significance); added the fair full-information baseline `central_best` (agent reuse, expected-quality objective) as the H2 and H6 reference; gave agents an informative track record so reliability is a real competence signal. Ran the full protocol (20 seeds, N from 50 to 1000) and filled the paper's Results and Discussion from it. Honest outcome: H1, H3, H4, H5, H7, H8 supported; H2 not supported (CTA reaches about 94 per cent of the fair optimum, 0.883 against 0.937, level with pull-based, the gap being Binding Energy's cost-awareness plus a noisy competence proxy); H6 not supported. `autorun` now accepts an optional protocol. Sixty tests pass; `ruff` clean.

- Tier 2 calibration depth: added Brier and ECE calibration-error metrics on winners (`engine._brier_ece`), reported under H7 (about 0.26 each under overconfidence); added `harness.track_record_sweep` (recovery and winner calibration versus the length of the reliability record, 2 to 40 prior attempts) with the `track_record_recovery.svg` figure and a `track_record` summary block. Finding: the correction is cheap in data, a two-attempt record already recovers most of the gap, and recovery and calibration both improve with a longer record. Sixty-two tests pass; `ruff` clean.

- Generalisability, sensitivity, and a dashboard: added a second generator family (`latent`, smooth cosine compatibility, no skill gate) threaded through `CellParams.family`; re-ran the population-dependent hypotheses under both families (H4, H7, H8 hold under both; H2 not under either). Added sensitivity bands (`recovery_vs_spread`, `reduction_vs_recall`) and a `recovery_surface` heatmap, new pure-SVG `heatmap`/`bar_chart` renderers and four figures, and a self-contained HTML dashboard (`cta dashboard`) that inlines every figure with the verdicts and the cross-generator comparison. Fulfils the paper's 2.7 generalisability commitment. Sixty-eight tests pass; `ruff` clean.

- H2 gap decomposition: added a `quality` selection mode (Binding Energy without the latency term) and `harness.h2_decomposition`, which splits the H2 quality gap into a latency (cost-for-speed) component and a competence-proxy component. A quality-first CTA reaches about 0.93, within the margin of the optimum, so roughly three quarters of the gap is the deliberate quality-for-latency tradeoff. New `h2_decomposition.svg` figure and dashboard entry; the paper's H2 row and Discussion updated. Sixty-nine tests pass; `ruff` clean.

- Live-pilot scaffold (Stage 2): `src/cta/pilot.py` now has a `PilotClient` seam (`assess`, `perform`), a deterministic `MockClient` that runs the whole pilot pipeline with no model calls, a guarded `ClaudeAgentClient` stub for the live path, and `run_pilot` which reuses eligibility, the barrier, reliability-weighted selection with an online track record, and the gate, reporting the calibration measures. Runnable via `cta pilot`. `tests/test_pilot.py` added. The live execution still needs the `llm` extra, real subagents, and budget approval, but the plumbing is ready and tested. Seventy-three tests pass; `ruff` clean.

- Realistic fleet and the reliability diagram: `src/cta/realism.py` builds a mixed fleet from calibration archetypes grounded in MarketBench (overconfident/calibrated/underconfident) and runs it through the pilot pipeline with a success-based self-report. The track-record correction still recovers completion (about 0.06 to 0.08), improves calibration, and the gate still cuts violations by about 0.8; the recovery stays positive across fleet compositions. Added the missing calibration visualisation (`engine.reliability_bins` + a reliability diagram) and a fleet-mix figure, wired into `autorun`, the dashboard, and the paper. `tests/test_realism.py` added. Seventy-eight tests pass; `ruff` clean.

- Live pilot executed with real Claude Code subagents: 3 agents x 13 coding micro-tasks with validated hidden tests, 39 real self-report-versus-outcome pairs. Real result: the agent is underconfident (stated ~0.92, delivered 1.0; gap ~-0.08, Brier 0.008), matching MarketBench's Claude finding and confirming real self-reports are miscalibrated. Suite, scorer, analyser, submissions, data, a real reliability diagram, `docs/live_pilot.md`, a paper paragraph, and `tests/test_live_pilot.py` are committed. Reproduce with `python -m pilot_tasks.analyse`. Next real-data step: a harder/larger suite and a mix of models to populate the overconfident region. Eighty-one tests pass; `ruff` clean.

## Now runnable end to end

`pip install -e ".[dev]"` then `cta autorun` runs the full deterministic
research pipeline and writes results and figures. The deterministic Auto-Researcher
loop (Stage 2) runs via `cta.autoresearch`.

## Not done yet

- Still open: the live LLM pilot execution (interface only in `pilot.py`) and an LLM-driven proposer for the loop; the concurrent-process swarm engine over the store for faithful contention; further sweeps to move H3, H4, and H5 from pending to tested (the infeasible and stall ground-truth check, the gate ablation, and the Ea by T stability grid); optional numeric extras (scipy Hungarian at large N, matplotlib figures); the paper's Results and Discussion filled from a full run; and publication to public GitHub (a human step pending GitHub connector authorisation).
- The paper's Results and Discussion are not yet filled from a full-scale run (demo results exist under `results/`).

## Next steps (ordered)

1. Deepen the calibration study: sweep the competence spread and the noise as well as the bias, add a calibration-error (Brier or ECE) measure over winners, and vary the track-record window to show how much history the correction needs. This is also the most promising way to rescue H6.
2. Close the H2 quality gap honestly: add a pure-quality selection mode (Binding Energy without the latency term) to show how much of the roughly 6 per cent gap to the fair optimum is the deliberate cost tradeoff, and report both.
3. Anchor the miscalibration parameters (bias, noise) to real language-model calibration numbers (for example MarketBench's stated-versus-realised success on SWE-bench), then run the live Claude Code pilot (`pilot.py`, interface only today) for real self-report and outcome data.
3. Build the concurrent-process swarm engine over the store for faithful contention, and the LLM-driven proposer plus the live Claude Code pilot (Stage 2, opt-in, cost-gated).
4. Product packaging polish and the pre-publication safety checklist, then publish to public GitHub (a human step pending GitHub connector authorisation).

## How to run what exists today

```
python -m pip install -e ".[dev]"
ruff check .
pytest
```
