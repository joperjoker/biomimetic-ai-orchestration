# Project Status

A running log of what is complete and what comes next. Read this, then `claude.md`, `docs/roadmap.md`, and `docs/measures.md` to resume in a fresh session.

## In one line

Chemotactic Task Allocation (CTA): decentralised, signal-driven orchestration of a swarm of coding agents, where a task wrapper scores an agent's role, skills, and prompt into a compatibility, an agent takes a task only when its compatibility reaches the task's activation energy, and a trust gate screens the winner before write access. This is AI coding-agent orchestration research; the biology is design inspiration only.

## North Star

The one claim under test: decentralised, signal-driven self-selection relieves the central-orchestrator bottleneck while holding match quality and safety. Sharpened after a literature comparison (decentralised self-selection is well covered): the contribution is calibration robustness. Self-assessment miscalibration is the failure mode of self-selection (the compatibility bid is the agent's own self-report, E13), and a track-record correction (the reliability R, E4) recovers the completion that miscalibration costs, with the integrity gate as a safety backstop. Motivated by MarketBench (Fradkin and Krishnan, 2026). Every addition serves that claim or is marked a consideration.

## Decisions locked

- Framing: AI coding-agent orchestration; biology as inspiration, not subject.
- Platform: self-contained, minimal. SQLite in WAL mode (transactional atomic claim) is the coordination store; an optional Postgres adapter exists. No external service in the default path.
- The task wrapper computes compatibility `c` from role, skills, and prompt via measurable sub-scores; activation is on compatibility (`c >= Ea`); the Binding Energy `B = c x C_tilde / L` ranks the willing agents only.
- Two stages run in order: Stage 1 deterministic simulation swarm, then Stage 2 the LLM stage (required, Claude Code agents).
- Scaling sweep to about 2000 agents. Licence Apache-2.0. Language Python 3.11+.

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
