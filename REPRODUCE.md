# Reproduce

The core needs only Python 3.11 or later and the standard library. There is no
external service in the default path.

## Install and check

```
python -m pip install -e ".[dev]"
ruff check .
pytest
```

## Run the autonomous research (Stage 1, deterministic)

```
cta autorun --out results
```

This runs the pre-registered sweeps across the four conditions (CTA, pull-based,
central greedy, central optimal), computes the statistics, evaluates the
hypotheses, and writes:

- `results/summary.json`: the full aggregated results and verdicts.
- `results/RESULTS.md`: a readable Results document with the hypothesis table.
- `results/figures/*.svg`: the scaling and heterogeneity figures (pure SVG, no
  plotting library required).

Use `--full` for the larger protocol (slower). Runs are deterministic: the same
command reproduces the same numbers.

## Auto-Researcher loop (Stage 2, deterministic search)

The propose, evaluate, keep-or-revert loop in `cta.autoresearch` tunes the
bounded search space (activation energy and temperature) to improve a protected
metric under a guardrail. It runs with no model calls. An LLM proposer can be
substituted without changing the loop or its guardrails.

## Notes

- Optional extras: `pip install -e ".[viz]"` adds numpy, scipy, and matplotlib
  (scipy gives the exact Hungarian assignment at large scale; without it a
  brute-force optimum is used for small instances and a greedy fallback beyond).
- The live pilot (a swarm of Claude Code subagents) is opt-in, needs the `llm`
  extra, and is gated by human approval of the cost budget.
