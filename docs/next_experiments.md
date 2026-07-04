# Next experiments: an executable plan to strengthen the paper

**Author of this plan:** Fable (analysis and planning).
**Executor:** Opus (writes the code, runs it, commits the data and figures).
**North Star:** a strong biomimicry AI paper backed by a *large* dataset that
confirms its hypotheses, resolves a real AI failure mode, and carries a credible
commercialisation story.

**Progress (the minimum-viable-paper cut line is done).** Completed and committed:
P0.1 (header), P0.2 (scaling fast path), P0.3 (repo hygiene), P1.0 (bounded-
information central baseline and the fair H9 comparison), P1.1 (bootstrap CIs and
power notes on the headline comparisons), P1.2 (scaling to N=10,000 with fitted
growth exponents 0.0 vs 2.0), P1.3 (raw dataset released as
`results/dataset/runs.csv`), P2.4 (biomimicry ablation isolating the barrier and
the gate), P2.3 (token and dollar cost model), P1.4 (one-command reproducibility),
P2.7 (heterogeneous specialist routing, H10), P2.2 (latency-quality Pareto), and
P2.6 (product PoC, `examples/poc`). Still open: P2.1 (fit generators to measured
calibration), P2.5 (two-sided live pilot, needs subagent budget), and all of
Phase 3 including P3.4 (the real-agent, dependency-graph follow-up).

**P2.7 landed (H10 supported).** The activation barrier holds specialist routing
at 1.00 across observability (chance floor 0.25); without it routing collapses to
0.47 under tight observability, at a coverage cost annealing (H5) reclaims. This
gave the barrier the quality role P2.4 found it lacking. The full real-agent,
dependency-graph version remains P3.4, a follow-up paper rather than a revision.
Next likely target: P2.1 (fit generators to measured calibration) or P2.6 (PoC).

**P2.2 landed.** The Binding Energy's latency term now carries a swept exponent,
tracing a non-dominated latency-quality frontier (quality about 0.91 at the
slowest, high-quality end down to about 0.87 as the bid favours faster agents);
with the cost model this is the second product dial.

This is a code-first plan. Every item names the concrete file and function to
add or change, the dataset or figure it produces, the paper section it feeds,
and an acceptance test that decides whether the item is done. Keep the house
rules throughout: pure Python standard library (no numpy/scipy), deterministic
under seeded `random.Random`, British English, no clause-separating dashes, no
puffery. `ruff check .` and `pytest` stay green after every item.

Read the two cross-cutting protocols first (statistics, and product). They bind
every experiment below and exist to stop the larger experiment family from
quietly turning into p-hacking or a demo with no customer.

---

## Where the paper stands, and the gaps this plan closes

The framework is built and the protocol is pre-registered. The honest weaknesses
a reviewer will find, and that block the four goals, are:

1. **The dataset is small for the claim.** 20 seeds, `N <= 1000`, 39 live-pilot
   samples. "Large dataset" is a stated goal and the evidence does not yet meet
   it, and the seed count was chosen by hand rather than by the effect size we
   need to detect.
2. **The central baseline has perfect information.** `run_central`
   (`baselines.py:150`) scores every pair from the *true* compatibility vectors,
   so it is an unbeatable oracle. H2 and H6 are measured against an opponent that
   cannot exist in production.
3. **Biomimicry is asserted, not isolated.** Nothing shows the biological
   mechanisms (activation barrier, integrity gate, annealing) beat a plain
   reliability-weighted auction. `selection_mode` already exists in `engine.py`
   (`SELECTION_MODES`), so the ablation has a hook but has never been run as one.
4. **Scaling is capped at N=1000 by an accident of implementation.**
   `run_central` builds the full assignment even when only the analytic
   coordinator cost (`N*M`, `baselines.py:164`) is reported, so large N is
   needlessly expensive.
5. **No cost, latency or dollar model, and no product definition.** The
   commercial claim has no Pareto frontier, no pricing, and no statement of what
   the product actually is or who buys it.
6. **H6 is dead by construction.** A decentralised scheme cannot beat a
   full-information optimum on quality, so "we match/beat central" is only fair
   once the baseline is information-bounded (couples to gap 2).
7. **The generators are hand-tuned, not fitted to real data.** External validity
   rests on one 39-sample pilot; the synthetic distributions are not anchored to
   any measured calibration data.

---

## Cross-cutting protocol A: statistics and pre-registration

Applies to every experiment. Do this before running the sweeps, not after.

- **Pre-register each new or re-run hypothesis.** Before writing results, add to
  `docs/paper.md` §2.6 a one-line falsification criterion for every new claim
  (H2/H6 vs the bounded baseline in P1.0, the four biomimicry conditions in P2.4,
  the streaming and adversary claims in Phase 3). State the direction, the metric
  and the threshold in advance.
- **Choose the seed count by power, not by hand.** Add `stats.min_seeds(effect,
  sd, alpha=0.05, power=0.8)` (a closed-form normal approximation, pure stdlib)
  and run it on a 20-seed pilot of each headline comparison to pick
  `headline_seeds`. Report the chosen number and the detectable effect. This
  replaces the arbitrary "200" with a justified figure (likely in the low
  hundreds, but derived).
- **One Holm family per results table.** When P1.0 and P2.x add comparisons, they
  join the existing Holm-Bonferroni family for their table so the corrected
  p-values stay honest as the family grows. Do not run the new tests in a
  separate, uncorrected family.
- **Reproducible, non-overlapping seeds.** Derive each condition's seed stream
  as `hash(condition_name) ^ base_seed + i` (or an explicit offset table) so no
  two conditions share draws and the whole dataset regenerates bit-for-bit.
  Add a test that two conditions do not collide.
- **Commit to reporting negatives.** Every hypothesis item below is "supported or
  the paper says it is not." A mechanism that does not earn its place (P2.4), a
  regime where CTA loses to the bounded baseline (P1.0), or annealing that does
  not help under streaming (P3.3) is a *result*, written up, not a run to bury.
- **Runtime budget.** Estimate wall-clock before the big run (`headline_seeds` x
  conditions x cells). If it exceeds a few minutes single-core, memoise per-seed
  cells and parallelise with `concurrent.futures` over seeds (determinism is per
  seed, so this is safe). Record the budget in `results/dataset/README.md`.

## Cross-cutting protocol B: the product thesis

The commercial goal needs a stated product, not just a cost curve. Write
`docs/product.md` (one page) and keep the experiments pointed at it:

- **What it is.** A decentralised task-allocation layer for multi-agent LLM
  systems: agents self-select on a calibrated, track-record-corrected bid behind
  an integrity gate, with no central scheduler to become the bottleneck or the
  single point of failure.
- **Who buys it and why now.** Teams running agent fleets who hit the coordinator
  `N*M` wall and cannot trust raw self-reports. Position explicitly against the
  central routers the literature already has (RouteLLM, EvoRoute, DiSRouter): the
  differentiator is *no central router* plus *calibration robustness*, not better
  routing accuracy.
- **The wedge deliverable.** A minimal runnable proof of concept (P2.6) a
  prospective user can run on their own agents, not only the simulator.
- Every commercialisation experiment (P2.2, P2.3, P2.6) must cite the number it
  produces back to a line in this doc (cost saved, latency dial, failures
  prevented). If an experiment does not move a product claim, it is Phase 3, not
  Phase 2.

---

## Phase 0: quick wins (unblock everything else)

### P0.1 Fix the stale "preliminary, demo scale" header
- **File:** `docs/paper.md`, the §3 Results header.
- **Change:** the body already reports the full protocol; delete the
  "(preliminary, demo scale)" qualifier so the section and its contents agree.
- **Acceptance:** a grep for "preliminary, demo scale" returns nothing.

### P0.2 Scaling fast path in the central baseline
- **File:** `src/cta/baselines.py`.
- **Change:** add `coordinator_cost(agents, tasks) -> dict` returning only the
  analytic load fields (`coordinator_work`, `total_work`, `peak_agent_work`,
  `peak_per_node`, all `N*M`; `peak_store_load` 0) without calling
  `greedy/best/optimal_assignment`. Give `run_central` a `quality: bool = True`
  parameter; when `False` it returns `coordinator_cost(...)` with zeroed quality
  fields. In `harness.scaling_sweep`, call the central condition with
  `quality=False` because the sweep only needs the load curve.
- **Acceptance:** `coordinator_cost` matches the old load fields exactly for a
  small fleet (regression test); `scaling_sweep` at `N=5000` completes in under a
  few seconds on one core.

### P0.3 Repo hygiene (keep the project tight)
- **Done in this pass:** removed four empty stub directories (`src/agents`,
  `src/gates`, `src/orchestrator`, `src/signals`) left from an abandoned
  architecture sketch; rewrote `architecture.md §9` from a "planned layout that
  never happened" into the actual `src/cta` layout; pointed P1.4 at the existing
  `REPRODUCE.md` rather than a duplicate.
- **Remaining judgment calls (do as docs are touched, not as a separate churn):**
  `docs/roadmap.md` is a pre-build plan that has partly diverged from what was
  built; when it is next edited, either mark it "historical plan" at the top or
  fold the still-live Auto-Researcher description into `architecture.md` and
  retire the rest. Check `claude.md` (298 lines), `STATUS.md` and `CHANGELOG.md`
  for overlap before each grows further; prefer one source of truth per fact.
- **Standing rule:** every new experiment adds at most one figure and one data
  file per claim, and reuses `viz.py`/`stats.py` rather than adding new plotting
  or stats helpers. No new top-level directories; new modules go under `src/cta`.
- **Acceptance:** `git ls-files` shows no empty-marker files; no doc describes a
  layout that does not exist; `ruff check . && pytest` stay green.

---

## Phase 1: a fair baseline, then the large dataset

**Sequencing note (this fixes a bug in the first draft of this plan):** the
information-bounded baseline (P1.0) changes what every headline number is
measured against, so it must land *before* the large dataset is frozen.
Generating the big dataset first and swapping the baseline second would force a
full regenerate and invalidate any interim write-up. Do P1.0, then P1.1 to P1.3.

### P1.0 Bounded-information central baseline (makes H2 and H6 fair)
- **File:** `src/cta/baselines.py`.
- **Change:** add `run_central_bounded(agents, tasks, rng, staleness, noise)`
  that assigns from *self-reported* compatibility with a *stale* reliability
  estimate, mirroring what a real coordinator sees. Define staleness concretely:
  the reliability used is the agent's value from `staleness` rounds ago (or, in
  the batch engine, `R` computed from a truncated history), and `noise` perturbs
  the self-report as in E13. **Fairness constraint:** the bounded central and CTA
  must be given the *same* information budget, so the comparison isolates
  central-versus-decentralised, not who was handed better data. State this in
  §2.3.
- **Feeds:** §2.3 baselines; §3 H2 and H6 re-run against the bounded baseline;
  §4 honest-negative discussion.
- **Acceptance:** at zero staleness/noise it reduces to perfect-info central
  (regression); as staleness rises its quality drops below CTA in at least one
  regime, giving H6 a beatable target; a Holm-corrected test reports it.

### P1.1 Power-justified seed count with confidence intervals
- **File:** `src/cta/harness.py` `Protocol`, `src/cta/stats.py`, `src/cta/cli.py`.
- **Change:** add `headline_seeds` set from `stats.min_seeds` (protocol A), used
  for the verdict table, robustness table and calibration sweep; keep the cheaper
  `seeds` for exploratory grids and surfaces. Make `aggregate` emit a percentile
  bootstrap 95% CI (pure stdlib, fixed seed) for every headline mean.
- **Feeds:** §3 verdict and robustness tables (every mean gains a CI); §2.6
  reports the power calculation.
- **Acceptance:** headline tables in `results/RESULTS.md` show `mean [lo, hi]`; a
  test checks the CI brackets the mean and narrows as seeds increase.

### P1.2 Extend the scaling curve and fit growth with CIs
- **File:** `src/cta/harness.py` `Protocol.scaling_n`, new `fit_scaling` in
  `src/cta/stats.py`.
- **Change:** extend `scaling_n` to `(50, 100, 200, 500, 1000, 2000, 5000,
  10000)` (feasible after P0.2). `fit_scaling` does an OLS fit of
  `log(peak_per_node)` on `log(N)` for central and decentralised, returning the
  exponent with a bootstrap CI.
- **Feeds:** §3 scaling; H1.
- **Acceptance:** the fitted central exponent CI includes the analytic slope and
  the decentralised per-node slope CI includes ~0; a log-log figure covers the
  full range.

### P1.3 Release the raw per-run dataset (the headline deliverable)
- **File:** new `src/cta/dataset.py` (`dump_runs`), `cta dataset` subcommand.
- **Change:** persist every per-seed, per-condition record (inputs: N, M, mode,
  bias, staleness, seed; outputs: mean quality, stall rate, violations, loads) to
  `results/dataset/runs.csv` via the stdlib `csv` module, plus
  `results/dataset/README.md` (data dictionary, seed scheme, runtime budget).
- **Feeds:** §3, the reproducibility appendix, and the product story (a shippable
  benchmark).
- **Acceptance:** `runs.csv` has one row per (condition, seed) with a stable
  column order; row count equals conditions times seeds; a test round-trips the
  CSV and re-derives one headline mean from it.

### P1.4 One-command reproducibility
- **File:** `src/cta/cli.py` (`cta reproduce-all`), extend the existing root
  `REPRODUCE.md` (do not create a second reproduce doc), pin the
  interpreter/toolchain versions in `pyproject.toml` and a short `constraints`.
- **Change:** a single entry point regenerates every figure, table and the CSV
  from seeds, documented by extending `REPRODUCE.md`. A paper stands or falls on
  this for a synthetic-data claim.
- **Acceptance:** `cta reproduce-all` on a clean checkout reproduces the committed
  figures and `runs.csv` byte-for-byte (or within a documented tolerance); CI-style
  smoke test runs it at small scale.

---

## Phase 2: realism, biomimicry and the product

### P2.1 Ground the generators in measured calibration data
- **File:** `src/cta/realism.py`, `src/cta/generators.py`.
- **Change:** fit the calibration-bias and noise distributions of the synthetic
  fleet to the measured MarketBench profiles already in `realism.PROFILES`
  (overconfident, calibrated, underconfident) instead of hand-picked constants,
  and add a `fitted` generator family that samples from them. This turns
  "synthetic supports the hypotheses" into "synthetic *calibrated to real
  measurements* supports the hypotheses."
- **Feeds:** §2.5 realism, §3 robustness (verdicts under the fitted family), §4
  external validity.
- **Acceptance:** the fitted family's aggregate bias/noise match the source
  profiles within tolerance (test); headline verdicts hold under it or the paper
  reports the difference.

### P2.2 Latency and quality Pareto frontier
- **File:** `src/cta/scoring.py` `binding_energy`, new `harness.pareto_sweep`.
- **Change:** the bid already divides by latency (`c_self * reliability / lat`,
  `engine.py:196`); expose a latency-weight exponent `beta` so the bid is
  `... / lat**beta` (`beta=1` is current behaviour, `beta=0` ignores latency).
  `pareto_sweep` sweeps `beta` and records realised quality against mean assigned
  latency, returning the non-dominated set.
- **Feeds:** new §3 Pareto paragraph; the "speed/quality dial" product claim in
  `docs/product.md`.
- **Acceptance:** `figures/pareto_latency_quality.svg` shows a monotone frontier;
  a test asserts the returned set is genuinely non-dominated.

### P2.3 Token and dollar cost model
- **File:** new `src/cta/cost.py`.
- **Change:** attach per-evaluation and per-execution token estimates to agents
  and a `PRICING` table of real per-model input/output rates (cite the source in
  a comment and the paper). Compute coordinator dollar cost of central (`N*M`
  evaluations at coordinator rates) versus decentralised (each agent pays for its
  own local evaluations), producing a cost-versus-N curve and a crossover point.
- **Feeds:** new §4 commercialisation subsection; `docs/product.md` cost claim.
- **Acceptance:** `figures/cost_vs_n.svg` shows central growing as `N*M` and
  decentralised linear per node; a test checks the crossover matches the analytics.

### P2.4 The biomimicry ablation (isolates the biology)
- **File:** `src/cta/engine.py` (reuse `selection_mode`), new
  `harness.biomimicry_ablation`.
- **Change:** four conditions: (a) full CTA (activation barrier + integrity gate
  + annealing), (b) minus the activation barrier, (c) minus the integrity gate,
  (d) a plain reliability-weighted auction with none of the biological mechanisms
  (`selection_mode` gives the bid variants; barrier and gate are toggled). Sweep
  all four across the calibration and adversarial regimes.
- **Feeds:** §2 (biomimicry moves from assertion to evidence), §3 ablation table,
  §4.
- **Acceptance:** the ablation table shows each biological mechanism contributes a
  measurable, Holm-corrected gain on at least one metric (quality, stall rate or
  violations), or the paper reports honestly that it does not.

### P2.5 Scale the live pilot to a two-sided reliability curve
- **File:** `pilot_tasks/suite.py`, `pilot_tasks/analyse.py`, `src/cta/pilot.py`.
- **Change:** add a harder task tier that induces genuine failures (populating the
  overconfident region of the reliability diagram), and run the pilot across at
  least two model tiers via independent subagents for per-model calibration. Keep
  the reference-validates-its-own-hidden-cases guard before spending any budget.
  Budget is spent only through sanctioned Claude Code subagents, never by
  scavenging credentials or endpoints.
- **Feeds:** §3 live pilot, external-validity anchor for H7; `docs/live_pilot.md`.
- **Acceptance:** the reliability diagram has points on *both* sides of the
  diagonal; per-model ECE and Brier are reported; every reference still passes its
  own hidden cases.

### P2.6 Product proof of concept (the commercial wedge)
- **File:** new `examples/poc/` with a small runnable demo and `docs/product.md`.
- **Change:** a minimal end-to-end example a prospective user runs on a handful of
  real subagents: define three toy agents, post tasks, watch them self-select
  through the calibrated gated bid, and print the allocation, the prevented
  violations and the coordinator cost avoided. This is the artefact that turns the
  paper into a product story rather than a table of simulations.
- **Feeds:** `docs/product.md`; a demo paragraph/figure in §4.
- **Acceptance:** `python -m examples.poc` runs end-to-end offline (mock client)
  and, when budget is available, with real subagents; a test runs the mock path.

### P2.7 Heterogeneous complex-task routing: binding and rejection with specialists (H10)
- **Why:** the paper never shows the binding energy routing qualitatively
  different subtasks to qualitatively different specialists. The synthetic sweeps
  use abstract compatibility vectors, and the live pilot was degenerate (one
  agent type, independent micro-tasks all solved by everyone), so self-selection
  had nothing to discriminate. This is the most face-valid gap left, and it is
  the setting most likely to give the activation barrier a *quality* role, which
  P2.4's batch ablation found neutral. Keep it dependency-free (parallel subtasks)
  so the allocation signal is not confounded by scheduling; the DAG version is the
  follow-up P3.4.
- **File:** new `with_specialist_roles` (a `roles` scenario) in
  `src/cta/generators.py`; new `harness.routing_experiment`; reuse `run_batch`,
  `eligible` and the integrity gate.
- **Change:** build a designed "job" of parallel subtasks, each tagged with a
  required role, skill and scope, and a fleet of role-specialised agents (high
  capability on their role, low elsewhere, tools and scope matching the role; the
  `domains` family at high heterogeneity already produces specialists). Inject
  miscast overclaimers, agents that self-report high fit for a role they cannot
  do. Measure routing accuracy (the fraction of subtasks whose winning agent is
  the ground-truth-correct specialist) and the deflection of miscast winners, with
  the activation barrier and the integrity gate each on and off.
- **Hypothesis H10:** the Binding Energy selection routes each subtask to its
  correct specialist (routing accuracy materially above a chance floor, and higher
  with the barrier than without), and the Rejection Gate plus the reliability
  correction deflect the miscast overclaimer. Report honestly if the barrier does
  not lift routing.
- **Feeds:** §2 (the division-of-labour biomimicry becomes evidence, not
  assertion), §3 (an H10 row and a figure), §4. It is the direct test of whether
  the barrier earns a quality role by keeping badly matched agents from firing.
- **Acceptance:** `figures/specialist_routing.svg`; a test that routing accuracy
  exceeds the chance floor and rises with the barrier, and that miscast-winner
  violations fall with the gate; deterministic under seeds. Effort is small, one
  generator plus one sweep plus one figure, because the engine and gate already
  exist.

---

## Phase 3: stretch (depth, only after Phases 0 to 2 land)

### P3.1 Concurrent multi-process engine over the SQLite store
- **File:** `src/cta/engine.py` / `src/cta/store.py`.
- **Change:** drive the atomic-claim store from several OS processes to
  demonstrate the decentralised claim under real contention. Measure claim-
  contention retries and wall-clock throughput versus N.
- **Acceptance:** no double-claims under contention (store invariant test); a
  throughput-versus-workers figure.

### P3.2 Strategic adversary that games the score and track record
- **File:** `src/cta/generators.py`, `src/cta/harness.py`.
- **Change:** an agent that inflates its self-report to win bids and later
  underperforms; measure how fast the reliability correction `R=(s+1)/(n+2)`
  detects and demotes it.
- **Acceptance:** the adversary's win share decays over rounds; the integrity gate
  and reliability jointly bound the damage; reported with CIs.

### P3.3 Streaming/dynamic task arrival in the temporal engine
- **File:** `src/cta/temporal.py`.
- **Change:** tasks arrive over time rather than as a fixed batch, testing the
  annealing schedule (H8/E14) under non-stationary load.
- **Acceptance:** quality and stall rate under streaming arrival are reported
  against the batch baseline; annealing still helps or the paper says it does not.

### P3.4 Real complex task in the wild: decomposition, dependencies, real specialists (follow-up)
- **Scope note:** this is the full form of the specialist-routing idea and the
  natural headline of a *follow-up* paper, not a revision of this one. It absorbs
  P2.5 (a harder, multi-model live suite) and P2.6 (the product PoC). The in-paper
  H10 (P2.7) is the dependency-free core that isolates the allocation signal; this
  item adds the real agents and the dependency graph on top, which is a separate,
  larger arc.
- **File:** builds on `src/cta/pilot.py`, `pilot_tasks/`, and `examples/poc/`
  (P2.6).
- **Change:** take a genuine complex job (for example a small feature that needs a
  designer, a backend developer and a test writer), decompose it into a subtask
  graph with dependencies, allocate it to real heterogeneous Claude subagents
  through the calibrated gated bid, and execute in dependency order. Measure
  end-to-end routing correctness, realised quality, prevented out-of-scope
  actions, and the whole job's cost and latency against a central-scheduler
  baseline. Budget is spent only through sanctioned Claude Code subagents.
- **Acceptance:** a real job is decomposed, allocated and executed end to end;
  each subtask reaches a correctly specialised agent or the miscast one is
  deflected; the job's total cost and latency are reported against the central
  baseline.

---

## Further planning threads (beyond the experiments)

These are not code experiments but they gate whether the paper and product land.
Plan them now so they do not surface as surprises late.

- **Submission target and format.** The paper is markdown. A real submission needs
  a named venue and a format (LaTeX or PDF), print-quality figures (the SVGs must
  survive black-and-white printing and small sizes), and a related-work table
  positioning CTA against RouteLLM, EvoRoute, DiSRouter and MarketBench. Decide
  the venue before P2 so the figure and length budget are known.
- **Threats-to-validity expansion.** Every new experiment adds a validity caveat
  (synthetic generators, single-repo pilot tasks, pricing assumptions in the cost
  model). Grow §2.7 in step, do not leave it as-is while the claims expand.
- **Responsible-deployment note.** The commercial angle needs a short paragraph on
  failure modes of the mechanism itself: agents gaming the integrity gate or the
  track record (this is what P3.2 measures), and what a deployer should monitor.
- **Artifact/data release.** For credibility and the product's "shippable
  benchmark" claim, plan a versioned release of `results/dataset/runs.csv` with a
  data card and a DOI (for example Zenodo). Couples to P1.3 and P1.4.
- **CI and test-strength.** Confirm `.github/workflows` runs `ruff` and `pytest`
  on every push, add a coverage floor, and consider property-based tests for the
  `store.py` atomic-claim invariant (no double-claims) since Phase 3 stresses it.

---

## Execution order, priority and the minimum viable paper

Work the phases in order; within a phase the items are independent and can be
parallelised. If time is short, the **minimum viable paper** (reviewer-ready) is:

> P0.1, P0.2, **P1.0** (fair baseline), P1.1 (power + CIs), P1.2 (scaling),
> P1.3 (dataset), P2.4 (biomimicry ablation), P2.3 (cost model).

Those eight close gaps 1 to 6 and give every core claim a figure, a CI and a
test. P2.1 (real-data grounding) and P2.6 (PoC) are the highest-value additions
beyond the minimum because they carry external validity and the product story.
P1.4, P2.2, P2.5 round it out. Phase 3 is optional depth.

Rough effort: P0 is hours; each P1 item is half a day; P2.1/P2.4 are the
heaviest in P2 (a day each) because they touch the engine and the write-up; P2.6
depends on subagent budget. Front-load P1.0 regardless, because everything
downstream is measured against it.

After each item: rerun the relevant sweep (or `cta reproduce-all`), refresh
`results/`, update the named paper section, run `ruff check . && pytest`, then
commit with a message naming the item (for example "P1.2: extend scaling to
N=10000 with fitted growth CIs"). Push to
`claude/biomimetic-ai-orchestration-init-0nb5db`. Each phase boundary updates
`STATUS.md` and `CHANGELOG.md`.

**Done when:** the dataset is released as CSV with power-justified CIs on every
headline mean (P1.1, P1.3); H2/H6 are measured against an information-bounded
baseline given an equal information budget (P1.0); the biomimicry ablation shows
each mechanism earns its place or reports it does not (P2.4); a cost/latency
Pareto and dollar model plus a runnable PoC back the commercial claim (P2.2,
P2.3, P2.6); the generators are anchored to measured data (P2.1); and the live
reliability curve is two-sided (P2.5). At that point the four goals (large
supporting dataset, biomimicry justified, AI failure mode resolved,
commercialisation credible) each have a figure, a test and a pre-registered
falsification criterion behind them.
