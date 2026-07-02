# Changelog

All notable changes to this project are recorded in this file. The format follows the spirit of Keep a Changelog, and the project aims to follow semantic versioning once a first release is cut.

## [Unreleased]

### Added

- Foundational workspace: directory layout separating signals, agents, gates, and the orchestrator.
- `README.md` with motivation, core concepts, an architecture diagram, and a worked Binding Energy example.
- `claude.md` as persistent master context: theory, equations, lifecycle, concurrency model, and validation criteria.
- `docs/theory.md` with the verified reference, a worked example, the reliability model, and the limits of the biological analogy.
- `docs/glossary.md` mapping biological terms to their engineering counterparts.
- Project hygiene: `.gitignore`, `pyproject.toml`, `CONTRIBUTING.md`, and a continuous integration workflow.
- Foundation guard test suite that checks structure, key documents, and the style constraints.
- Apache License 2.0 (`LICENSE`), and the confirmed language decision (Python 3.11 or later).
- Two-stage selection frame: a binary eligibility filter followed by an activation-energy barrier (`BE >= Ea`), with a deterministic threshold default and an optional Arrhenius temperature extension, plus the distinct infeasible and stalled outcomes.
- Research draft (`docs/paper.md`): introduction (problem, prior art, contributions, research questions) and methodology (design, formal model, baseline, variables and metrics, procedure, analysis, validity and threats), with verified references.
- Formal framework (Chemotactic Task Allocation) with numbered equations E1 to E14 and cost accounting C1 to C3, unifying eligibility, Binding Energy, activation, the claim, the trust gate, an independent quality model, and self-assessment noise.
- Five methodology refinements: bottleneck-focused scaling (total, coordinator, and communication cost), contention and herding metrics, construct validity via an independent quality model and self-assessment noise, the reality gap elevated to the primary external threat with a real-agent pilot as future work, and threshold-stability analysis (new H5).
- The response threshold model (Bonabeau et al., 1996) added as the precedent for the activation barrier, plus references for market-based coordination (Dias et al., 2006) and multi-agent LLM failure modes (Cemri et al., 2025).
- Experimental architecture (`docs/architecture.md`): a dual-mode design (Python simulation for scale, a real-swarm pilot of Claude Code subagents over Supabase Postgres for ecological validity), the shared scoring core and central baseline as controls, a genuine atomic-claim coordination store, a metric-to-measurement map, and the evaluation protocol.
- Research North Star and evaluation architecture logged to `claude.md` for memory.
- Implementation roadmap (`docs/roadmap.md`): the agent harnesses, an Auto-Researcher loop adapted from Karpathy's AutoResearch (kept on a leash by the Rejection Gate with pre-registered metrics, sandboxing, and human gates), and the plan to shape the repository as the public report. Plan only, not yet built.

- Context and memory layer for the Auto-Researcher (the Recursive Language Models principle: Zhang, Kraska, and Khattab, 2025, arXiv:2512.24601): treat the event log and ledger as an external environment that is queried and recursively summarised under depth and budget caps, with deterministic and logged sub-calls, to mitigate context rot. Documented in `docs/architecture.md`, `docs/roadmap.md`, and the paper's analysis; a reliability technique of the research process, separate from the CTA contribution.

- Implementation started (Phase A): the `cta` package with `src/cta/scoring.py`, the measurable model E1 to E11 as pure, dependency-light functions (compatibility from role, skills, and prompt; eligibility; reliability; effective capability; Binding Energy; activation and firing; tie breaker; winner selection; gate), with twenty-one unit tests. Packaged via `pyproject.toml` with a `src` layout.
- `STATUS.md`: a running log of completed work, locked decisions, and the ordered next steps for the whole research.
- Implementation Phase B: `src/cta/store.py`, the self-contained SQLite store (WAL) with the transactional atomic claim, the tasks, agents, events, and attempts tables, and a reliability read. A concurrency test confirms exactly one winner among 32 contending claimers.
- Implementation Phases H, I, and J: `src/cta/viz.py` (pure-SVG charts), `src/cta/report.py` (hypothesis verdicts and a Results writer), and `src/cta/cli.py` with the `cta autorun` command (registered as a console script). One command runs the sweeps, computes statistics, evaluates H1 to H6, and writes `results/summary.json`, `results/RESULTS.md`, and SVG figures. Committed demo results are included.
- Implementation Phases F and G: `src/cta/stats.py` (confidence intervals, Mann-Whitney U, Cliff's delta, Holm-Bonferroni, all pure standard library) and `src/cta/harness.py` (the four conditions across seeds, scaling and heterogeneity sweeps, aggregation to mean and confidence interval). Forty tests pass.
- Implementation Phases C to E (in-process): `src/cta/quality.py` (ground-truth Q), `src/cta/generators.py` (seeded populations with a heterogeneity control), `src/cta/engine.py` (the `run_batch` event loop for the `cta` and `pull_based` conditions with a metrics summary), and `src/cta/baselines.py` (central greedy and optimal assignment, optimal via scipy when available or brute force for small instances). Thirty-three tests pass; an end-to-end smoke runs across 200 agents and 150 tasks.

### Changed

- Consistency pass across the documents: standardised the effective-capability symbol on `C_tilde` and stated the reliability coupling as the default (ablatable); aligned the metric lists in `docs/theory.md` and `claude.md` with the authoritative set in `docs/paper.md` section 2.4 (realised quality with the Binding Energy proxy, and coordinator work); linked the Auto-Researcher loop and the experiment ledger into `docs/architecture.md` and the paper's analysis; unified "coordinator work" wording; and refreshed the README status and layout.
- Re-audit after adding the context layer: standardised on the correct name Recursive Language Models (RLM), confirmed the RLM material is scoped to the research process, and re-verified notation, metric lists, and cross-references.
- Measurable model (`docs/measures.md`) and the task wrapper: every quantity is given a concrete, measurable definition. Compatibility `c` (from an agent's role, skills, and prompt) replaces the abstract signal `S`, and the activation barrier is now on compatibility (`c >= Ea`) with the Binding Energy `B = c x C_tilde / L` used only to rank the willing agents. Compatibility aggregates measurable sub-scores (semantic match, skill coverage, scope fit) and can be calibrated to predict realised success. Ground-truth quality, cost, complexity, and the activation energy are all defined operationally. The paper (sections 1 and 2.2), theory, glossary, and claude.md are reconciled, and the stale Supabase references are replaced with the self-contained store.
- Reference verification: confirmed all nine references online, corrected the Kuhn issue number to 2(1-2), added the missing in-text citation for Dias et al. (2006), added DOIs for Kuhn, Gerkey, Dorigo, and Smith, and cleared the now-confirmed Recursive Language Models verification flags.
- Principal-level review (AI, mathematics, and science) with judged revisions: added three principal personas to the Consortium; added a decentralised pull-based baseline to isolate CTA's mechanisms from decentralisation; made agent heterogeneity a first-class variable with RQ6 and H6; added multiple-comparison control, a power note, and explicit falsification criteria; sharpened the novelty statement; and documented that `L` is a normalised relative cost so the absolute `Ea` is interpretable.
