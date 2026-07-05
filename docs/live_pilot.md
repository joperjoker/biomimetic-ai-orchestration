# Live pilot: measured calibration of a real coding agent

The simulation and the MarketBench-grounded fleet both model miscalibration
rather than observe it. This pilot observes it directly: a real Claude coding
agent states its confidence on coding micro-tasks, then actually solves them, and
we score the solutions against hidden edge-case tests. It is the external-validity
anchor for H7 (self-reports are miscalibrated) using real self-reports and real
outcomes.

## Method

- **Tasks.** Thirteen self-contained Python micro-tasks (`pilot_tasks/suite.py`),
  each with a spec the agent sees and a set of hidden cases including edge cases
  the spec does not spell out. Every reference solution is checked to pass its own
  hidden cases (`suite.validate()`), so the scoring is trustworthy.
- **Agents.** Three independent Claude Code subagents, each given only the specs.
  For each task an agent states a confidence in [0, 1] (its probability of passing
  all hidden cases, including the unstated edge cases) and then writes the
  solution, in one shot, using no tools.
- **Scoring.** Each solution is executed and scored against the hidden cases
  (`pilot_tasks/score_submissions.py`); `pilot_tasks/analyse.py` computes the
  calibration and draws the reliability diagram.

Reproduce the scoring and the figure from the committed submissions:

```
python -m pilot_tasks.analyse
```

## Result

Across 3 agents x 13 tasks (39 attempts) the agent solved every task, at a mean
stated confidence of about 0.92. So on this suite the real agent is
**underconfident**: it under-promises and over-delivers.

| Measure | Value |
|---------|-------|
| attempts | 39 (3 agents x 13 tasks) |
| mean stated confidence | 0.92 |
| mean realised pass rate | 1.00 |
| overconfidence gap (stated minus realised) | -0.08 |
| Brier score | 0.008 |
| ECE | 0.078 |

The reliability diagram (`results/figures/reliability_live.svg`) shows the agent's
points sitting **above** the diagonal of perfect calibration, the signature of
underconfidence.

## Reading it honestly

Two things this does and does not show.

- It **confirms the premise**: a real coding agent's self-reports are
  miscalibrated (the gap is not zero), so calibration is a real concern for
  self-selection, not a synthetic artefact. The direction here, underconfidence,
  matches MarketBench's finding that the Claude models are well calibrated to
  underconfident, while other models (a Gemini-class model in that study) are
  sharply overconfident. Miscalibration is real and its sign is model-dependent,
  which is exactly why a correction that reweights by an observable track record,
  and is agnostic to the direction of the bias, is the right fix.
- It **does not** populate the overconfident, failure region of the curve,
  because this strong agent solved the whole suite. A full two-sided reliability
  curve needs either harder tasks that induce failures or a more overconfident
  model (for example the Gemini-class behaviour MarketBench reports). That is the
  natural next spend: a larger, harder task suite and a mix of models.

## Hard tier: two model families, 114 attempts

We extended the suite to nineteen tasks by adding six harder
overconfidence-trap tasks (`my_atoi`, `compare_version`, `simplify_path`,
`decode_string`, `calculate`, `is_number`), each with subtle hidden edge cases
(integer clamping, truncation toward zero, numeric-string grammar). We then ran
two model families over the full nineteen tasks under the same closed-book,
no-tools protocol: three Claude Opus 4.8 agents and three Claude Haiku 4.5
agents.

Reproduce the hard-tier scoring and figure:

```
python -c "from pilot_tasks.analyse import analyse; \
analyse('results/live_pilot/hard', 'results/live_pilot/hard', \
'results/figures/reliability_live_hard.svg')"
```

| Measure | Value |
|---------|-------|
| attempts | 114 (6 agents x 19 tasks) |
| model families | 2 (Opus 4.8, Haiku 4.5) |
| mean stated confidence | 0.93 |
| mean realised pass rate | 1.00 |
| overconfidence gap (stated minus realised) | -0.074 |
| Brier score | 0.007 |
| ECE | 0.074 |

Every one of the 114 attempts passed, including all six trap tasks, at a mean
stated confidence of 0.93. **Both families are competent and uniformly
underconfident** on these solvable, in-distribution tasks: neither the frontier
model nor the small model produced a single overconfident point
(`results/figures/reliability_live_hard.svg`). The harder tier did not move the
sign of the miscalibration.

The honest reading is a directional result the simulation cannot assume away:
on solvable in-distribution coding tasks, real-agent miscalibration is
**underconfidence**, not overconfidence. That has a concrete allocation
consequence. A naive self-report auction would then **under-select** capable
agents (raising the stall rate and leaving tasks unclaimed), rather than
over-selecting bad ones; the track-record correction helps because it
recalibrates the bid regardless of the direction of the bias. Overconfidence,
the failure mode the synthetic bias sweep spans, is an out-of-distribution
phenomenon here: it needs tasks beyond a model's competence, or a model family
that is overconfident in-distribution (the Gemini-class behaviour MarketBench
reports). Populating the overconfident arm of the curve is therefore a deliberate
task-design or model-choice exercise, not something a harder tier of standard
algorithmic problems delivers.

## Capability ladder x wrapper ablation (expert tier)

The hard tier above shows both Claude families at the ceiling, so it cannot
separate model capability or show what CTA's wrappers buy. For that we built a
harder, trap-dense expert tier of eight tasks (`pilot_tasks/expert_suite.py`:
repeating-decimal formatting, English number words, full text justification, a
parenthesised calculator, big-integer string multiply, minimum window substring,
word break, wildcard matching) whose references are hard-checked against
canonical outputs. Three model families spanning least to most capable, Haiku
4.5, Sonnet 5 and Opus 4.8, each solved the tier under two conditions:

- **bare**: the unwrapped prompt (signature and one line).
- **task-wrapped**: the CTA **task wrapper**, the full envelope with the
  acceptance criteria and the edge cases named plus a self-check contract.

Real per-run telemetry (tokens, wall-clock) is recorded in
`results/live_pilot/ladder/telemetry.json`. Reproduce with `python -m
pilot_tasks.ladder`.

**The capability ladder (bare).** Completion (fraction of the eight tasks fully
passed) rose with model capability: Haiku 0.875, Sonnet 1.00, Opus 1.00. Haiku's
single miss was `is_match`, which it coded with regular-expression semantics
(`*` as "zero or more of the preceding") instead of wildcard semantics (`*` as
"any sequence") in one of its two runs, an honest weak-model slip on the hardest
task. Sonnet and Opus were already at the ceiling.

**The task wrapper (`ladder_completion.svg`, `ladder_wrapper_lift.svg`).**
Wrapping the task lifts the weakest model to the ceiling and leaves the strong
ones unchanged: Haiku's completion rose from 0.875 to 1.00 (+0.125 completion,
+0.05 fidelity), while Sonnet and Opus stayed at 1.00 (they had nowhere to gain).
The wrapper's acceptance criterion for `is_match` ("`*` matches any sequence
including empty") named exactly the distinction Haiku had missed, and both wrapped
Haiku runs then wrote the correct wildcard solution. The task wrapper helps most
where the model is weakest, which is the point: it raises the floor.

**The agent wrapper (`ladder_cost_fidelity.svg`).** The agent wrapper is CTA
Binding-Energy routing across the ladder: each task goes to the cheapest model
whose reliability-corrected self-report clears the activation barrier. Running the
identical router under the two conditions is the clean contrast:

| Routing over | Completion | vs always-Opus | Cost saving | Latency |
|---|---|---|---|---|
| bare tasks | 0.875 | 1.00 | 51x cheaper | ~neutral |
| task-wrapped tasks | 1.00 | 1.00 | 47x cheaper | ~neutral |

With bare tasks the router sends work to the cheap model and **loses completion**
(0.875): Haiku's self-report on `is_match` is overconfident, its overall track
record is good, so the corrected bid clears the barrier and the task is routed to
a model that fails it, exactly the miscalibration failure mode the paper studies.
Add the task wrapper and the cheap model becomes genuinely reliable, so the same
routing **keeps completion at the frontier level (1.00) at about one forty-seventh
of the always-Opus cost** (representative economy-versus-premium price tiers from
`cta.cost`). The two wrappers are complementary: the task wrapper raises the weak
model's fidelity, and the agent wrapper turns that into a cost saving by routing
away from the expensive model. The saving here is in cost, not latency; on these
runs the small model was not faster, so we report the latency multiple as roughly
neutral rather than claim a speed win.

This is the commercialisation story in one experiment: a well-designed task
wrapper lets a cheap model do frontier-quality work, and a calibrated agent
wrapper routes to it, so a fleet reaches the strongest model's completion at a
fraction of its cost. The sample is small (eight tasks, two agents per cell) and
the price tiers are representative rather than a live quote, so the multiples are
illustrative of the mechanism, not a benchmark figure.
