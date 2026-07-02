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
- Code, Phase B: `src/cta/store.py`, the self-contained SQLite store (WAL mode) with the transactional atomic claim, the four tables (tasks, agents, events, attempts), event append, attempt recording, and a reliability read. A concurrency test in `tests/test_store_atomic.py` confirms that among 32 contending claimers exactly one wins. All tests pass; `ruff` clean.

## Not done yet

- Code Phases C to M: ground-truth quality; population generators (with heterogeneity); synthetic and Claude Code agents; the simulation engines (event loop and concurrent swarm); baselines (Hungarian, greedy, pull-based); the Rejection Gate module wiring; the experiment harness and configs; metrics and statistics; visualisation; the report generator; `cta autorun`; the Auto-Researcher LLM loop and the context layer; the live pilot; product packaging.
- No results, figures, or filled Results and Discussion sections yet.

## Next steps (ordered)

1. Phase C to E: the ground-truth quality model, seeded population generators (with heterogeneity), the synthetic and Claude Code agents, the two simulation engines (event loop and concurrent swarm over the store), and the three baselines (Hungarian, greedy, pull-based).
2. Phase F to I: harness and configs, metrics and statistics, visualisation, and the report generator that fills the paper.
3. Phase J: `cta autorun`, the demo config, and the CI smoke run. After this the system is ready and the user can say "start" to run the autonomous research.
4. Phase K and L: the Auto-Researcher LLM loop (with the context layer and guardrails) and the opt-in live pilot, run in order after Stage 1.
5. Phase M: product packaging, `REPRODUCE.md`, README quickstart, and the pre-publication safety checklist, then publish to public GitHub (a human step pending GitHub connector authorisation).

## How to run what exists today

```
python -m pip install -e ".[dev]"
ruff check .
pytest
```
