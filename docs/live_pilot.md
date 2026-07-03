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
