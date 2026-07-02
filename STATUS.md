# Project Status

A running log of what is complete and what comes next. Read this, then `claude.md`, `docs/roadmap.md`, and `docs/measures.md` to resume in a fresh session.

## In one line

Chemotactic Task Allocation (CTA): decentralised, signal-driven orchestration of a swarm of coding agents, where a task wrapper scores an agent's role, skills, and prompt into a compatibility, an agent takes a task only when its compatibility reaches the task's activation energy, and a trust gate screens the winner before write access. This is AI coding-agent orchestration research; the biology is design inspiration only.

## North Star

The one claim under test: decentralised, signal-driven self-selection relieves the central-orchestrator bottleneck while holding match quality and safety. Every addition serves that claim or is marked a consideration.

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
- Code, Phase K (deterministic Stage 2): `src/cta/autoresearch/` (`search_space.py` and `loop.py`), the propose, evaluate, keep-or-revert loop that tunes the bounded search space (activation energy and temperature) to improve a protected metric under a guardrail, with a decision ledger. It runs with no model calls; an LLM proposer can be substituted without changing the loop. `src/cta/pilot.py` defines the live-pilot interface (opt-in, not executed). `REPRODUCE.md` and a CI autorun smoke are in place.
- Code, Phases H, I, and J: `src/cta/viz.py` (pure-SVG line charts, zero dependencies), `src/cta/report.py` (hypothesis verdicts H1 to H6 and a Results Markdown writer), and `src/cta/cli.py` (`cta autorun`, the one-command autonomous run). Registered as the `cta` console script. Running `cta autorun` produces `results/summary.json`, `results/RESULTS.md`, and SVG figures. At demo scale H1 and H2 are supported, H6 is not supported (reported faithfully), and H3 to H5 are pending the concurrent engine and further sweeps. This is the "start"-ready milestone.
- Code, Phases F and G: `src/cta/stats.py` (confidence intervals, Mann-Whitney U with tie correction via `statistics.NormalDist`, Cliff's delta, Holm-Bonferroni) and `src/cta/harness.py` (the four conditions run across seeds, with a scaling sweep and a heterogeneity sweep, and aggregation to mean and 95 per cent confidence interval). Tests in `tests/test_analysis.py`. Pure standard library.
- Code, Phases C to E (in-process): `src/cta/quality.py` (ground-truth Q, E12), `src/cta/generators.py` (seeded agent and task populations with the heterogeneity control), `src/cta/engine.py` (the fast event-loop `run_batch` for the decentralised conditions `cta` and `pull_based`, returning per-task outcomes and a summary), and `src/cta/baselines.py` (central greedy and optimal assignment, with the optimal using scipy when available or a brute-force optimum for small instances). Tests in `tests/test_sim.py`. All 33 tests pass; `ruff` clean. An end-to-end smoke over 200 agents and 150 tasks runs and shows the expected shape (CTA matches pull-based quality at much lower coordinator work, and beats central greedy on mean quality).

## Now runnable end to end

`pip install -e ".[dev]"` then `cta autorun` runs the full deterministic
research pipeline and writes results and figures. The deterministic Auto-Researcher
loop (Stage 2) runs via `cta.autoresearch`.

## Not done yet

- Still open: the live LLM pilot execution (interface only in `pilot.py`) and an LLM-driven proposer for the loop; the concurrent-process swarm engine over the store for faithful contention; further sweeps to move H3, H4, and H5 from pending to tested (the infeasible and stall ground-truth check, the gate ablation, and the Ea by T stability grid); optional numeric extras (scipy Hungarian at large N, matplotlib figures); the paper's Results and Discussion filled from a full run; and publication to public GitHub (a human step pending GitHub connector authorisation).
- The paper's Results and Discussion are not yet filled from a full-scale run (demo results exist under `results/`).

## Next steps (ordered)

1. Run the full protocol (`cta autorun --full`) and fill the paper's Results and Discussion from the output; commit the figures.
2. Add the sweeps that resolve H3, H4, and H5 (infeasible and stall ground-truth check, gate ablation, Ea by T stability).
3. Build the concurrent-process swarm engine over the store for faithful contention, and the LLM-driven proposer plus the live Claude Code pilot (Stage 2, opt-in, cost-gated).
4. Product packaging polish and the pre-publication safety checklist, then publish to public GitHub (a human step pending GitHub connector authorisation).

## How to run what exists today

```
python -m pip install -e ".[dev]"
ruff check .
pytest
```
