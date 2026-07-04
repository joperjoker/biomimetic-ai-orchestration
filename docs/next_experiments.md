# Next experiments: an executable plan to strengthen the paper

**Author of this plan:** Fable (analysis and planning).
**Executor:** Opus (writes the code, runs it, commits the data and figures).
**North Star:** a strong biomimicry AI paper backed by a *large* dataset that
confirms its hypotheses, resolves a real AI failure mode, and carries a credible
commercialisation story.

This is a code-first plan. Every item names the concrete file and function to
add or change, the dataset or figure it produces, the paper section it feeds,
and an acceptance test that decides whether the item is done. Work the phases in
order; within a phase the items are independent and can be parallelised. Keep
the house rules throughout: pure Python standard library (no numpy/scipy),
deterministic under seeded `random.Random`, British English, no
clause-separating dashes, no puffery. `ruff check .` and `pytest` stay green
after every item.

---

## Where the paper stands, and the six gaps this plan closes

The framework is built and the protocol is pre-registered. The honest weaknesses
that a reviewer will find, and that block the four goals, are:

1. **The dataset is small for the claim.** 20 seeds, `N <= 1000`, 39 live-pilot
   samples. "Large dataset" is a stated goal and the evidence does not yet meet
   it.
2. **The central baseline has perfect information.** `run_central` scores every
   pair from the *true* compatibility vectors, so it is an unbeatable oracle.
   H2 and H6 are measured against an opponent that cannot exist in production.
3. **Biomimicry is asserted, not isolated.** Nothing shows the biological
   mechanisms (activation barrier, integrity gate, annealing) beat a plain
   reliability-weighted auction. Without that ablation the biology is decoration.
4. **Scaling is capped at N=1000 by an accident of implementation.**
   `run_central` builds the full assignment even when only the analytic
   coordinator cost (`N*M`) is reported, so large N is needlessly expensive.
5. **No cost, latency or dollar model.** The commercial claim has no Pareto
   frontier and no pricing.
6. **H6 is dead by construction.** A decentralised scheme cannot beat a
   full-information optimum on quality, so "we match/beat central" can only be
   fair once the baseline is information-bounded (see gap 2).

The phases below close these in dependency order.

---

## Phase 0: quick wins (unblock everything else)

### P0.1 Fix the stale "preliminary, demo scale" header
- **File:** `docs/paper.md`, the §3 Results header.
- **Change:** the body already reports the full protocol; delete the
  "(preliminary, demo scale)" qualifier so the section and its contents agree.
- **Feeds:** §3.
- **Acceptance:** no occurrence of "preliminary, demo scale" remains; a grep for
  it returns nothing.

### P0.2 Scaling fast path in the central baseline
- **File:** `src/cta/baselines.py`.
- **Change:** add `coordinator_cost(agents, tasks) -> dict` that returns only the
  analytic load fields (`coordinator_work`, `total_work`, `peak_agent_work`,
  `peak_per_node`, all `N*M`; `peak_store_load` 0) without calling
  `greedy/best/optimal_assignment`. Give `run_central` a `quality: bool = True`
  parameter; when `False` it returns `coordinator_cost(...)` merged with zeroed
  quality fields. In `harness.scaling_sweep`, call the central condition with
  `quality=False` because the sweep only needs the load curve, not the assigned
  quality.
- **Feeds:** §3 scaling result; unlocks P1.2.
- **Acceptance:** `coordinator_cost` matches the old `run_central` load fields
  exactly for a small fleet (regression test); `scaling_sweep` at `N=5000`
  completes in under a few seconds on one core; a new test asserts the fast path
  and the full path agree on the four load fields.

---

## Phase 1: the large dataset (the headline goal)

### P1.1 Raise the seed count for the headline hypotheses
- **File:** `src/cta/harness.py` `Protocol` dataclass and `src/cta/cli.py`
  `autorun`.
- **Change:** add `headline_seeds: int = 200` alongside the existing
  `seeds: int = 20`. Use `headline_seeds` for the verdict table, the robustness
  table and the calibration sweep; keep the cheaper `seeds` for exploratory grids
  and surfaces so the run stays tractable. Confidence intervals must be reported,
  so make `aggregate` emit a bootstrap 95% CI (percentile bootstrap, pure stdlib,
  fixed seed) for every headline mean.
- **Feeds:** §3 verdict and robustness tables (every mean gains a CI).
- **Acceptance:** headline tables in `results/RESULTS.md` show `mean [lo, hi]`;
  a test checks the CI brackets the mean and narrows when seeds increase.

### P1.2 Extend the scaling curve and fit growth with CIs
- **File:** `src/cta/harness.py` `Protocol.scaling_n` and a new
  `fit_scaling(rows) -> dict` in `src/cta/stats.py`.
- **Change:** extend `scaling_n` to `(50, 100, 200, 500, 1000, 2000, 5000,
  10000)` (feasible now that P0.2 removed the assignment cost). `fit_scaling`
  does an ordinary-least-squares fit of `log(peak_per_node)` on `log(N)` for both
  central and decentralised, returning the exponent with a bootstrap CI, to back
  the "central grows as N*M, decentralised stays flat per node" claim
  quantitatively.
- **Feeds:** §3 scaling; H1.
- **Acceptance:** the fitted central exponent CI includes the analytic slope and
  the decentralised per-node slope CI includes ~0; a scaling figure covers the
  full range on a log-log axis.

### P1.3 Release the raw per-run dataset
- **File:** new `src/cta/dataset.py` with `dump_runs(path, rows)` and a
  `cta dataset` CLI subcommand in `src/cta/cli.py`.
- **Change:** persist every per-seed, per-condition record (inputs: N, M, mode,
  bias, seed; outputs: mean quality, stall rate, violations, loads) to
  `results/dataset/runs.csv` using the stdlib `csv` module, plus a short
  `results/dataset/README.md` data dictionary. This *is* the "large dataset"
  deliverable a reader can reanalyse.
- **Feeds:** §3, reproducibility appendix, and the commercialisation story (a
  shippable benchmark).
- **Acceptance:** `runs.csv` has one row per (condition, seed) with a stable
  column order; row count equals conditions times seeds; a test round-trips the
  CSV and re-derives one headline mean from it.

---

## Phase 2: realism, biomimicry and commercialisation

### P2.1 A bounded-information central baseline (makes H2 and H6 fair)
- **File:** `src/cta/baselines.py`.
- **Change:** add `run_central_bounded(agents, tasks, rng, staleness, noise)`
  that assigns from *self-reported* compatibility with a stale reliability
  estimate rather than the true vectors, mirroring what a real coordinator would
  actually see. This is the honest opponent: a scheduler with imperfect
  knowledge, which CTA's local track-record correction can plausibly match or
  beat.
- **Feeds:** §2.3 baselines, §3 (rerun H2 and H6 against the bounded baseline),
  §4 discussion of the honest negative.
- **Acceptance:** at zero staleness/noise it reduces to the perfect-info central
  (regression); as staleness rises its quality degrades below CTA on at least
  one regime, giving H6 a beatable target; a Holm-corrected test reports the
  comparison.

### P2.2 Latency and quality Pareto frontier
- **File:** `src/cta/scoring.py` `binding_energy` and new
  `harness.pareto_sweep`.
- **Change:** `binding_energy` currently trades quality against a length term
  `L`; expose the L weight as a swept parameter. `pareto_sweep` sweeps it and
  records realised quality against mean task latency (proxy: assigned task
  length), returning the non-dominated set.
- **Feeds:** new §3 Pareto paragraph; commercial "tune the speed/quality dial"
  story.
- **Acceptance:** a `figures/pareto_latency_quality.svg` shows a monotone
  frontier; a test asserts the returned set is actually non-dominated.

### P2.3 Token and dollar cost model
- **File:** new `src/cta/cost.py`.
- **Change:** attach a per-evaluation and per-execution token estimate to agents
  and a `PRICING` table of real per-model input/output rates (cite the source in
  a comment and in the paper). Compute the coordinator dollar cost of central
  (`N*M` evaluations at coordinator rates) versus decentralised (each agent pays
  for its own local evaluations), producing a cost-versus-N curve.
- **Feeds:** new §4 commercialisation subsection; the product case.
- **Acceptance:** `figures/cost_vs_n.svg` shows central cost growing as `N*M` and
  decentralised growing linearly per node; a test checks the crossover point is
  where the analytics say it is.

### P2.4 The biomimicry ablation (isolates the biology)
- **File:** `src/cta/engine.py` `selection_mode` and new
  `harness.biomimicry_ablation`.
- **Change:** define four conditions: (a) full CTA (activation barrier + integrity
  gate + annealing), (b) minus the activation barrier, (c) minus the integrity
  gate, (d) a plain reliability-weighted auction with none of the biological
  mechanisms. Sweep all four over the calibration and adversarial regimes.
- **Feeds:** §2 (biomimicry justification moves from assertion to evidence), §3
  ablation table, §4.
- **Acceptance:** an ablation table shows each biological mechanism contributes a
  measurable, Holm-corrected gain on at least one metric (quality, stall rate or
  violations); if a mechanism does not, the paper reports that honestly.

### P2.5 Scale the live pilot to a two-sided reliability curve
- **File:** `pilot_tasks/suite.py`, `pilot_tasks/analyse.py`, `src/cta/pilot.py`.
- **Change:** add a harder task tier that induces genuine failures (so the
  overconfident region of the reliability diagram is populated, not just the
  underconfident one), and run the pilot across at least two model tiers via
  independent subagents to get per-model calibration. Keep the reference-validates
  -its-own-hidden-cases guard before spending any budget.
- **Feeds:** §3 live pilot, the external-validity anchor for H7; `docs/live_pilot.md`.
- **Acceptance:** the reliability diagram has points on *both* sides of the
  diagonal; per-model ECE and Brier are reported; every reference still passes
  its own hidden cases.

---

## Phase 3: stretch (depth, only after Phases 0 to 2 land)

### P3.1 Concurrent multi-process engine over the SQLite store
- **File:** `src/cta/engine.py` / `src/cta/store.py`.
- **Change:** drive the existing atomic-claim store from several OS processes to
  demonstrate the decentralised claim under real contention, not just simulated
  rounds. Measure claim-contention retries and wall-clock throughput versus N.
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

---

## Execution order and definition of done

1. Do **P0** first: it unblocks scale (P0.2) and removes a visible inconsistency
   (P0.1).
2. Do **P1** next: it produces the large dataset that is the headline goal.
3. Do **P2** for realism, the biomimicry evidence and the commercial story; P2.1
   and P2.4 are the highest-leverage because they turn two soft claims into fair,
   evidenced results.
4. **P3** is optional depth.

After each item: rerun `cta autorun` (or the relevant sweep), refresh `results/`,
update the named paper section, run `ruff check . && pytest`, then commit with a
message naming the item (for example "P1.2: extend scaling to N=10000 with fitted
growth CIs"). Push to `claude/biomimetic-ai-orchestration-init-0nb5db`. Each
phase boundary is a natural checkpoint to update `STATUS.md` and `CHANGELOG.md`.

**Done when:** the dataset is released as CSV with CIs on every headline mean
(P1.3, P1.1); H2/H6 are measured against an information-bounded baseline (P2.1);
the biomimicry ablation shows each mechanism earns its place or is reported not to
(P2.4); a cost/latency Pareto and dollar model back the commercial claim (P2.2,
P2.3); and the live reliability curve is two-sided (P2.5). At that point the four
goals — large supporting dataset, biomimicry justified, AI failure mode resolved,
commercialisation credible — each have a figure and a test behind them.
