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
passed) rose with model capability: over five Haiku agents Haiku reached 0.925
(bootstrap 95 per cent CI [0.85, 1.00]) against Sonnet and Opus at 1.00. Haiku's
residual misses were on `is_match`, which it sometimes coded with
regular-expression semantics (`*` as "zero or more of the preceding") instead of
wildcard semantics (`*` as "any sequence"), an honest weak-model slip on the
hardest task. Sonnet and Opus were already at the ceiling.

**The task wrapper (`ladder_completion.svg`, `ladder_wrapper_lift.svg`).**
Wrapping the task lifts the weakest model to the ceiling and leaves the strong
ones unchanged: Haiku's completion rose from 0.925 to 1.00 (+0.075 completion),
while Sonnet and Opus stayed at 1.00 (they had nowhere to gain). The wrapper's
acceptance criterion for `is_match` ("`*` matches any sequence including empty")
named exactly the distinction Haiku had missed, and the wrapped Haiku runs then
wrote the correct wildcard solution. The task wrapper helps most where the model
is weakest, which is the point: it raises the floor.

**The agent wrapper (`ladder_cost_fidelity.svg`).** The agent wrapper is CTA
Binding-Energy routing across the ladder: each task goes to the cheapest model
whose reliability-corrected self-report clears the activation barrier. Running the
identical router under the two conditions is the clean contrast:

| Routing over | Completion | vs always-Opus | Cost saving | Latency |
|---|---|---|---|---|
| bare tasks | 0.925 | 1.00 | 50x cheaper | ~neutral |
| task-wrapped tasks | 1.00 | 1.00 | 47x cheaper | ~neutral |

Over task-wrapped tasks the cheap model is genuinely reliable, so routing **keeps
completion at the frontier level (1.00) at about one forty-seventh of the
always-Opus cost** (representative economy-versus-premium price tiers from
`cta.cost`). Over bare tasks routing reaches 0.925: the cheap model's residual
`is_match` failures are the gap, which the wrapper closes. The router escalates by
task, using a per-task reliability, so it would send a task to a stronger model
whenever the cheap model's corrected bid on that task falls below the barrier; on
this tier, once a five-agent track record accrues, the cheap model clears the
barrier on every task, so the router keeps the work cheap and the wrapper carries
the completion. (An earlier two-agent sample put `is_match` just under the barrier
and escalated it, an artifact the larger sample corrected.) The two wrappers are
complementary: the task wrapper raises the weak model's fidelity, and the agent
wrapper turns that into a cost saving by routing away from the expensive model.
The saving here is in cost, not latency; on these runs the small model was not
faster, so we report the latency multiple as roughly neutral.

This is the commercialisation story in one experiment: a well-designed task
wrapper lets a cheap model do frontier-quality work, and a calibrated agent
wrapper routes to it, so a fleet reaches the strongest model's completion at a
fraction of its cost. The sample is small (eight tasks, one to five agents per
cell) and the price tiers are representative rather than a live quote, so the
multiples are illustrative of the mechanism, not a benchmark figure.

## The project tier: a dependency graph, decomposition and assembly (P3.4)

The ladder uses flat, independent tasks. To exercise the wrappers on real
software with a **dependency graph and specialist modules**, we built the
miniquery project (`pilot_tasks/project_suite.py`): a small in-memory query
toolkit of five modules, `parse` (lex and parse a query), `match` (evaluate a
predicate against a row), `select` (filter rows, depending on parse and match),
`summarize` (aggregate a numeric field) and `render` (format a text table). The
dependency `select -> {parse, match}` and the need for the modules to share one
interface are the point. Each of the three model families built the whole project
under a **bare** spec (a loose paragraph) and a **task-wrapped** spec (the exact
interface contract and acceptance criteria per module). Reproduce with `python -m
pilot_tasks.project`.

**Bare: every model fails the project.** Under the loose spec, each model made a
self-consistent but divergent interface choice, and none delivered a project that
met the hidden contract: Haiku passed 2 of 5 modules, Sonnet 1, Opus 1, and the
whole-project completion was 0 for all three. The recurring divergence was the
`parse` return shape (Sonnet and Opus returned tuples `(field, op, value)` where
the contract wanted `{"field","op","value"}` dicts) and the `render` layout (both
added a separator line the contract did not ask for). Capability did not rescue
integration: Opus failed the project as surely as Haiku, because the failure is
about an unstated interface, not code quality.

**A calibration signal falls out.** Under the ambiguous bare spec the stronger
models correctly lowered their confidence (Sonnet mean 0.43, Opus 0.62), while
the weakest model stayed overconfident (Haiku 0.89 on a 2-of-5 result). Stronger
models were better calibrated about specification ambiguity. This is the same
miscalibration the paper studies, now at the level of a software interface.

**The task wrapper makes the project integrate.** With the exact interface
contract, all three models delivered a fully conforming project: 5 of 5 modules
and completion 1.0 across the board (a completion lift of +1.0 for every model),
and their confidence rose to a well-calibrated 0.84 to 0.93. The interface
contract, not model capability, is what turns independently built modules into a
working whole.

**The agent wrapper assembles a project from the cheapest parts
(`project_modules.svg`).** We then route each module to the cheapest model whose
reliability-corrected self-report clears the barrier, take that model's code for
the module, and assemble the pieces into one namespace:

| Assembling over | Assembled project | Cost vs always-Opus |
|---|---|---|
| bare modules | fails (completion 0.0) | 44x cheaper |
| task-wrapped modules | **works (completion 1.0)** | **39x cheaper** |

Over task-wrapped modules the assembled, cross-model project runs and passes at
about one thirty-ninth of the always-Opus cost. Over bare modules the assembly
fails even though it cherry-picks the best module from each model: the router can
find a conforming `parse`, `match` and `select` (Haiku's bare `parse` happened to
return dicts), but no model produced a conforming `render` or a fully correct
`summarize` without the contract, so the project cannot be completed at any price.
This is decomposition, routing and specialists in one experiment: the task
wrapper's interface contract is the precondition for a swarm to build software,
and the agent wrapper then delivers that software at the cheapest model's cost.
The sample is small (one agent per cell, five modules) and the prices are
representative tiers, so the multiples illustrate the mechanism rather than
benchmark it.
