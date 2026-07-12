# Experimental Architecture

This document describes the system architecture for evaluating Chemotactic Task Allocation (CTA). It is written so that the controls, measurements, metrics, and evaluations are all concrete and doable. The formal model it measures is in `docs/paper.md` section 2.2, and the narrative theory is in `docs/theory.md`.

## 1. Purpose and scope

The research validates one claim: that decentralised, signal-driven self-selection relieves the central-orchestrator bottleneck while holding match quality and safety. The architecture therefore has to do three things well: run the CTA framework and a centralised baseline under identical conditions, record every event so that metrics are recoverable, and support both large-scale runs and a real agent swarm.

## 2. Dual-mode design

Evaluation runs in two modes that share one core:

- Mode A, simulation: many synthetic agents in Python. It provides scale (large `N`), determinism, and cheap parameter sweeps. It produces the scaling curves and hypotheses H1 to H5.
- Mode B, real-swarm pilot: a small swarm of Claude Code subagents competing over a shared task pool in a self-contained store (SQLite in WAL mode by default). It provides ecological validity: real self-assessment, latency, cost, and output quality. It discharges the reality-gap threat.

Shared across both modes: the scent-envelope schema, the scoring module (equations E1 to E11), the event-log schema, and the metric computations. This shared core is the central control, because it isolates the effect of coordination from every other factor.

## 3. Component diagram

```
        +--------------------------+
        |   experiment harness     |  seeds, config, sweeps, conditions
        +------------+-------------+
                     | generates paired populations
                     v
   +----------------------------------------------+
   |        coordination substrate (SQLite)       |
   |  tasks | agents | events (log) | attempts    |
   +----+----------------------+------------------+
        ^  atomic claim (CAS)   |  append-only telemetry
        |                       v
  +-----+------+        +---------------+        +------------------+
  | CTA agents |        | central       |        |  analysis layer  |
  | (swarm or  |        | baseline      |        |  metrics, stats, |
  | simulated) |        | scheduler     |        |  scaling curves  |
  +-----+------+        +-------+-------+        +------------------+
        |                       |
        |  shared scoring module (E1 to E11): elig, compatibility c, C, L, R, B, P_fire
        v                       v
  +--------------------------------------+
  |   Rejection Gate (reliability + integrity)   |
  +--------------------+-------------------------+
                       | admitted
                       v
                +--------------+
                |  execution   |  outcome quality Q feeds back to reliability
                +--------------+
```

## 4. Components

1. Coordination substrate (self-contained: SQLite in WAL mode by default, with an optional Postgres adapter behind the same interface). Four tables:
   - `tasks`: identifier, envelope (jsonb: domain, eligibility as required capabilities, permissions, and tools, `Ea`, priority, expected cost, scope), status (one of CREATED, ADVERTISED, CLAIMED, EXECUTING, COMPLETED, FAILED, INFEASIBLE, STALLED), `claimed_by`, `run_id`, `condition`, and timestamps.
   - `agents`: identifier, capability profile, permissions, tools, `run_id`.
   - `events`: append-only telemetry, one row per event (see section 6).
   - `attempts`: reliability history (agent, task, success, `Q`, timestamp) used to compute `R = (s + 1) / (n + 2)` over a window `W`.
2. Atomic claim (equation E10). Under a transaction, `BEGIN IMMEDIATE; UPDATE tasks SET status='CLAIMED', claimed_by=? WHERE id=? AND status='ADVERTISED'` then check the changed row count. SQLite locking under WAL guarantees exactly one winner; losing agents see zero changed rows and move on. This is the real compare-and-swap that the theory assumes, not an approximation, and it needs no external service.
3. Scoring module (shared Python library). Pure functions `elig`, `compatibility` (the wrapper, `c`), `C`, `L`, `R`, `B`, `P_fire`, and `tie_break`. The simulation agents, the pilot agents, and the central baseline all call the same module, so scoring is never a confound.
4. Agents:
   - Simulation: coroutines with synthetic capability vectors and a ground-truth outcome model. They poll the pool, compute `B`, fire, attempt the claim, and produce a realised quality `Q` from the ground-truth function with noise.
   - Pilot: Claude Code subagents. Each reads the advertised tasks, and the wrapper computes compatibility `c` from the subagent's role, skills, and prompt; the subagent self-assesses `c`, `C`, and `L` (the miscalibration under study, equation E13), fires when the estimated compatibility reaches `Ea`, attempts the atomic claim, passes the gate, then executes a real micro-task in an isolated git worktree and reports `Q` as the test pass fraction.
5. Rejection Gate (shared). Admits when reliability `R >= tau` and the proposed action passes an integrity check (the change stays within the declared scope, enforced by a path allowlist and a safety lint). Otherwise it deflects and the task is re-advertised.
6. Baseline conditions (the controls). Three baselines share the scoring module and populations with CTA. Two are centralised schedulers that each round score all eligible pairs and assign by the Hungarian method (optimal) or greedy (naive), then execute and log identically; they measure the coordinator cost that a decentralised design avoids. The third is a decentralised pull-based work queue where agents self-schedule by claiming the best available eligible task, without the activation barrier or the Rejection Gate; comparing CTA against it isolates CTA's mechanisms from decentralisation alone.
7. Experiment harness. Seeded generators for agent and task populations, paired so the same populations feed every condition; configuration for `N`, `M`, arrival rate, the `Ea` distribution, `T`, `tau`, `W`, self-assessment bias and noise, and seed; and the ablations (gate on or off, deterministic versus Arrhenius, `Ea` sweep, noise sweep, `N` sweep).
8. Analysis layer. Reads the `events` table and computes metrics and statistics (means, 95 per cent confidence intervals, Mann-Whitney U tests, effect sizes) and the scaling curves. A Vercel dashboard for visualisation is a consideration, not a requirement.
9. Auto-Researcher loop. An optional meta-agent that speeds the study by proposing changes within a bounded search space, running time-boxed experiments through the simulation harness, and keeping a change only when it improves a protected, pre-registered metric without breaching a guardrail (otherwise it reverts with git). It is kept on a leash by the Rejection Gate applied to its own changes, with human gates for search-space changes, merges, and publication. The full design is in `archive/planning/roadmap.md`.
10. Experiment ledger. An append-only record of every Auto-Researcher decision (proposal, config hash, seeds, metric before and after, significance, safety verdict, keep or revert), so the research is auditable and reproducible.
11. Context and memory layer (Recursive Language Models principle). To keep long research campaigns reliable, the Auto-Researcher does not hold the full history in its prompt, which would invite context rot (quality decay as the prompt grows). Instead it treats the event log, the experiment ledger, and the documents as an external environment that it queries, following the Recursive Language Models strategy (Zhang, Kraska, and Khattab, 2025): it issues scoped retrievals (for example, configurations tried near a point in the search space, or results for a parameter) and recursively summarises large results through sub-agents, then aggregates. Guardrails: a maximum recursion depth and a per-call token and time budget; deterministic sub-calls (temperature 0, fixed seed) so runs reproduce; every recursive call logged to the ledger; and the store treated as the reproducible ground truth, with digests as rebuildable caches. Claude Code subagents are the recursion substrate. This is a reliability technique of the research process, not part of the CTA contribution.

## 5. Controls

- Shared scoring module across all conditions, so only coordination differs.
- Paired populations with fixed seeds: the same tasks and agents feed the decentralised and central conditions.
- The central baseline is the control; ablations attribute effects (gate on or off for the gate, `T` toward 0 versus `T > 0` for stochastic firing).
- The deterministic mode (`T` toward 0) is used for exact reproduction.
- A warm-up period is excluded from measurement.
- Matched small-`N` configurations are run in both modes to calibrate the simulation against the pilot.

## 6. Metric to measurement map

Every metric is a query over the `events` table. Event types are ADVERTISE, EVALUATE, ELIGIBLE, FIRE, CLAIM_ATTEMPT, CLAIM_WIN, CLAIM_LOSE, GATE_ADMIT, GATE_DEFLECT, EXEC_START, EXEC_DONE, QUALITY, INFEASIBLE, STALL, and ANNEAL, each carrying a payload (for example `B`, `S`, `C`, `L`, `Ea`, `Delta`, `Q`, latency, tokens, cost).

| Metric | How it is measured |
|--------|--------------------|
| Allocation latency | `ts(CLAIM_WIN) - ts(ADVERTISE)` per task |
| Coordinator work `W_coord` | count of CLAIM_ATTEMPT per task (decentralised), or scheduler comparisons per round (central) |
| Total evaluation work `W_eval` | count of EVALUATE events |
| Communication | database operations (or messages) per allocated task |
| Claim contention | CLAIM_ATTEMPT divided by CLAIM_WIN |
| Wasted evaluation | (FIRE minus CLAIM_WIN) divided by FIRE |
| Herding | Gini over tasks of the per-task FIRE count |
| Match quality | mean `Q` of winners from QUALITY events, with mean `B` at win as the proxy |
| Infeasible rate, stall rate | counts over `M`, checked against generator ground truth (confusion matrix for H3) |
| Deflection rate | GATE_DEFLECT divided by CLAIM_WIN, false deflection from ground-truth reliability or audit |
| Load fairness | Gini over agents of completed-task counts |
| Stability | variance of allocation rate over time windows, and maximum stall duration |
| Starvation | maximum terminal-minus-created time |
| Throughput | completed tasks per wall-clock time |
| Scaling | latency and `W_coord` as functions of `N` |
| Calibration sensitivity | quality and deflection versus the bias and noise sweep |
| Pilot cost | tokens, currency, and latency per task from Claude Code usage |

## 7. Evaluation protocol

- H1 (scaling): sweep `N`; compare the growth of `W_coord` and latency for the framework against the central baseline; fit curves; Mann-Whitney U per `N`; report effect sizes.
- H2 (quality): compare realised quality `Q` for the framework against the Hungarian optimum, using a pre-registered margin.
- H3 (expressiveness): compare labelled infeasible and stall outcomes against the generator's ground truth (precision and recall).
- H4 (trust): compare gate on against gate off under injected unreliability, on integrity and completion.
- H5 (stability): sweep the `Ea` by `T` grid; measure stability and maximum stall; confirm that annealing bounds stall time.
- Reality gap: run matched small-`N` configurations in both modes and compare metric distributions to quantify and calibrate the gap.

## 8. Doability and limits

- The SQLite schema, the atomic claim, and the logging are the Python standard library, so no external service or account is needed; an optional Postgres adapter exists for anyone wanting a distributed pilot.
- The Claude Code swarm is small (for example 3 to 8 concurrent subagents) because of cost and concurrency, so the scaling claim rests on the simulation, while the pilot supplies ecological validity rather than scale. Pilot agents work in isolated git worktrees to avoid clobbering shared state.
- The added complexity is justified by the hypotheses: heterogeneous agents are needed to make eligibility and matching meaningful, dynamic task arrival is needed to exercise stall, starvation, and stability, and the ablations are needed to attribute effects. Complexity beyond that is out of scope for now.

## 9. Actual layout

The implementation landed as a single package, `src/cta`, rather than the separate top-level directories this document originally anticipated. The mapping is: the simulation harness and run scripts are `harness.py`, `engine.py`, `temporal.py` and `cli.py`; the scoring and metrics are `scoring.py`, `quality.py` and `stats.py`; the baselines are `baselines.py`; the generators and realistic fleet are `generators.py` and `realism.py`; the Auto-Researcher loop and its bounded search space are the `cta.autoresearch` subpackage (`loop.py`, `search_space.py`); the real-agent pilot is `pilot.py` with the task suite under `pilot_tasks/`; reporting and figures are `report.py`, `dashboard.py` and `viz.py`; and the durable task pool, atomic claim and event log are `store.py` (SQLite). Committed data and figures live under `results/`. The forward-looking experiment plan is `archive/planning/next_experiments.md`.
