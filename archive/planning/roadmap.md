# Implementation Roadmap

> Historical planning document. It records the original pre-build plan and its
> proposed `src/agents`, `src/gates`, `src/orchestrator` layout, which the build
> did not follow: the framework shipped as the single `src/cta` package (see
> `docs/architecture.md` section 9). The forward plan is now
> `docs/next_experiments.md`. Kept for provenance.

This roadmap records the agreed plan for moving from write-up to build: the harnesses for each agent, an Auto-Researcher loop that speeds the work while staying reliable and safe, and the shaping of this repository as the final public report. It is a plan, not a record of completed work. The North Star is unchanged: show that decentralised, signal-driven self-selection relieves the central-orchestrator bottleneck while holding match quality and safety.

## 1. Auto-Researcher, adapted from Karpathy's AutoResearch

AutoResearch (Karpathy, 2026) runs an experiment loop under three constraints: a single modifiable surface, a single objectively testable metric, and a fixed time budget per experiment. The loop proposes a change, runs it, evaluates it, then keeps the change if the metric improved or reverts it with git if not. Karpathy pairs this with a reliability stance (keep AI on a leash): chained agent errors compound, so prefer small, verifiable, human-reviewed changes, and do not produce more than a human can review.

This project suits that loop, because Chemotactic Task Allocation (CTA) already has objective metrics (coordinator work, latency, realised quality) and a safety gate. The loop searches CTA design choices automatically, and it is kept on a leash by the project's own Rejection Gate applied to the loop's own changes. This self-consistent safety story is a design choice, not a proven result.

## 2. Assumptions (revisable)

- Stack: Claude Code subagents as the swarm; a self-contained SQLite store (WAL mode) for the task pool, atomic claim, event log, and reliability store, so no external service is needed; an optional Postgres adapter behind the same interface for anyone wanting a distributed pilot.
- Pilot task type: scoped software micro-tasks in this repository, with objective quality (test pass fraction).
- Auto-Researcher autonomy: time-boxed, sandboxed, revertible experiments run without approval; human approval is required to change the search space, to merge to the default branch, and to publish.
- Primary objective for the loop: minimise coordinator work per task and allocation latency, subject to guardrails (realised quality at or above a pre-registered margin, and safety and fairness not degraded). A single scalar objective is held in a protected metrics module.

## 3. Agent harness architecture

All harnesses share one contract, so they are interchangeable and testable: typed configuration in, structured event records out to the event log, fixed seeds, explicit time and cost budgets, and no writes outside a sandbox until the gate admits. A common `Harness` base defines `setup(config, seed)`, `run()`, `teardown()`, and `emit(event)`.

- Worker (CTA swarm) agent harness (`src/agents/`): `observe(pool)`, `assess(task) -> (S, C, L)`, `decide(task) -> fire?` (E7 to E9), `claim(task) -> won?` (E10, atomic), `execute(task) -> outcome` (only after gate admission), `report(quality)`. The simulation variant uses synthetic capability vectors and a ground-truth outcome model; the pilot variant is a Claude Code subagent that self-assesses (the miscalibration under study, E13), works in an isolated git worktree, and returns the test pass fraction as `Q`. Safety: a path allowlist from the task scope, resource and time budgets, and full logging.
- Central baseline scheduler harness (`src/orchestrator/baseline.py`): each round, pull advertised tasks and available agents, score all pairs with the shared module, assign by the Hungarian method (optimal) or greedy (naive), dispatch, execute, and log. This is the control condition.
- Rejection Gate harness (`src/gates/`): `(agent, proposed_action, scope) -> (admit?, reason)` from a reliability check (`R >= tau`), an integrity and scope check, and a safety lint. Applied to CTA agents and, by dogfooding, to the Auto-Researcher's own proposed changes.
- Simulation harness (`sim/`): a seeded population generator, an event-loop engine with task arrivals, the ground-truth quality model, and an event log writer. Deterministic and offline (SQLite). Produces the H1 to H5 curves.
- Auto-Researcher harness (`autoresearch/`), the loop: `propose() -> change` (edits only the search space), `run(change) -> metrics` (a time-boxed simulation batch), `evaluate(metrics) -> verdict` (against the protected primary metric and guardrails, over multiple seeds), `commit_or_revert(verdict)`, then `log(decision)` to the ledger. Kept changes become commits, so the git history becomes the research narrative. The loop reads its history through the context and memory layer (below) rather than holding it all in the prompt.
- Context and memory layer (`context/`), the Recursive Language Models principle: treat the event log, the ledger, and the docs as an external environment; `retrieve(query, budget) -> records`, `summarise(records, budget) -> digest`, and `recurse(chunks, depth) -> aggregate`, with Claude Code subagents as the recursion substrate. It keeps the Auto-Researcher reliable over a long campaign by avoiding context rot.
- Analysis and report harness (`analysis/`): read the event log, compute the metric-to-measurement map in `docs/architecture.md` (means, 95 per cent confidence intervals, Mann-Whitney U, effect sizes), and regenerate the figures and tables under `results/`.
- Experiment ledger and provenance (`docs/experiment-ledger.md` and a `ledger` table): an append-only record of every loop decision (proposal, config hash, seeds, metric before and after, significance, safety verdict, keep or revert), so the research is auditable and reproducible.

## 4. Auto-Researcher reliability and safety guardrails (the leash)

- Constrained surface: the loop may edit only `search_space/` (a configuration plus a bounded heuristics module: the `Ea` policy, temperature schedule, tie-break, and annealing delta). It may never edit the metrics, the ground-truth quality, the tests, or the gate; those are protected and changeable only by a human.
- Anti-metric-hacking: pre-registered primary and guardrail metrics, held read-only to the loop. An improvement that degrades a protected dimension (quality, safety, fairness) is rejected.
- Statistical honesty: a change is kept only when the improvement is significant across multiple seeds, not from a single lucky run.
- Sandboxing: experiments run in isolated git worktrees; nothing reaches the default branch without the gate and a human merge.
- Budgets and kill-switches: time, compute, and token or cost caps per experiment and per session; automatic stop on anomalies; no external network side effects during experiments.
- Human-in-the-loop gates: changing the search space, merging to the default branch, and publishing all require a human, and batches are sized so a human can review them.
- Provenance: the ledger and the gate reasons give a full audit trail.
- Context-rot mitigation: the loop uses the external-memory context layer (the Recursive Language Models principle: Zhang, Kraska, and Khattab, 2025) rather than holding the full history in its prompt, retrieving and recursively summarising from the event log and ledger under a depth and budget cap, with deterministic and logged sub-calls. See `docs/architecture.md`.

## 5. The repository as the report (public-ready)

- `README.md`: landing and abstract, a results summary, a reproduce-in-one-command pointer, and a short safety statement.
- `docs/paper.md`: the paper (introduction and methodology now; results and discussion once runs exist).
- `docs/architecture.md`: the system architecture.
- `docs/safety.md` (planned): the leash design, what the loop may and may not touch, the guardrails, and known failure modes.
- `results/` (planned): committed figures, tables, and derived metric files, each tied to a config hash and seed.
- `REPRODUCE.md` (planned): one-command reproduction of the simulation results.
- `docs/experiment-ledger.md` (planned): the Auto-Researcher decision log.
- Continuous integration runs the deterministic simulation and the tests, so visitors get green reproducibility.

Pre-publication checklist (a human gate): a secret scan (any API keys or tokens stay in environment variables, never committed), the licence present (Apache-2.0, done), disclaimers that the biology is design intuition only, a clean history, and a statement of limitations. Making the repository public and any pull request operations need the GitHub connector to be authorised, so publication is a human or authorised step.

## 6. Phased roadmap

- Phase 1, shared scoring module: `src/` with `elig, S, C, L, R, B, P_fire, tie_break` (E1 to E11) and a deterministic test fixture. Verify with known-value tests.
- Phase 2, simulation harness: `sim/` with seeded generators, the event loop, the ground-truth quality model, and SQLite logging. Verify that a fixed seed reproduces identical metrics.
- Phase 3, central baseline: `src/orchestrator/baseline.py` (Hungarian and greedy). Verify the first H1 and H2 comparison in simulation.
- Phase 4, analysis and report: `analysis/` computes the metric map and writes `results/`. Verify that figures regenerate from the logs.
- Phase 5, Rejection Gate: `src/gates/` with reliability, integrity, scope, and a safety lint. Verify the gate ablation under injected unreliability (H4).
- Phase 6, Auto-Researcher loop (simulation only first): `autoresearch/`, `search_space/`, the `context/` memory layer, the ledger, and the guardrails in section 4. Human gate: approve the search space. Verify that kept changes have significant, reproducible gains without breaching a guardrail, and that the context layer keeps the loop within budget without loading full history.
- Phase 7, real-swarm pilot: the store schema (`tasks, agents, events, attempts`, SQLite by default) and the atomic claim; Claude Code subagent workers in worktrees; the simulation-versus-pilot calibration. Human gate: approve pilot runs and the cost budget.
- Phase 8, repo-as-report and publication: `docs/safety.md`, `REPRODUCE.md`, `results/`, and the paper's results and discussion. Human gate: the pre-publication checklist and the switch to public.

## 7. Verification strategy

- Determinism: fixed seeds and config hashes; the deterministic firing path (`T` toward 0) reproduces runs exactly.
- Tests: unit tests for the scoring module and the gate, a smoke test for each harness, and the existing foundation and style guards kept green.
- Statistics: improvements accepted only with confidence intervals and a significance test across seeds.
- Safety: the loop cannot touch protected files (a path check in the loop plus code review), a secret scan before any push, and sandboxed execution.
- Reproducibility: `REPRODUCE.md` and continuous integration regenerate the committed results.

## 8. Open decisions and dependencies

- Confirm the four assumptions in section 2.
- GitHub connector authorisation is required before publishing or any pull request operation.
- No external service is needed; the pilot runs on the self-contained SQLite store. An optional Postgres or Supabase adapter is available for a distributed pilot, with any keys kept in environment variables and never committed.

## 9. References to add (verify primary sources before citing in the public paper)

- Karpathy, A. (2026) AutoResearch, the associated loop, and the reliability commentary. Verify against the primary repository and posts, since current detail comes from secondary write-ups.
- The AI Scientist-v2 (Sakana AI, 2025) and related closed-loop AI research systems, for related work.
- Cemri et al. (2025), already cited, for the multi-agent failure modes that motivate the leash.
- Zhang, A.L., Kraska, T., & Khattab, O. (2025) Recursive Language Models. arXiv:2512.24601. The external-memory principle for context-rot mitigation. Verified against the primary source (arXiv, submitted 31 December 2025).
