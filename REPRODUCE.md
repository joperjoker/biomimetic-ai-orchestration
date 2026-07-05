# Reproduce

The core needs only Python 3.11 or later and the standard library. There is no
external service in the default path.

## Install and check

```
python -m pip install -e ".[dev]"
ruff check .
pytest
```

## Reproduce everything with one command

```
cta reproduce-all --out results
```

This regenerates every table, figure and the raw dataset from seeds, so the whole
Results section can be rebuilt from source. It is the full protocol plus the
dataset in one deterministic entry point.

## Run the autonomous research (Stage 1, deterministic)

```
cta autorun --out results
```

This runs the pre-registered sweeps across the six conditions (CTA, pull-based,
central greedy, central optimal, central best, central bounded), computes the
statistics, evaluates the hypotheses, and writes:

- `results/summary.json`: the full aggregated results and verdicts.
- `results/RESULTS.md`: a readable Results document with the hypothesis table.
- `results/figures/*.svg`: the scaling, calibration, ablation, cost and other
  figures (pure SVG, no plotting library required).
- `results/dataset/runs.csv`: the raw per-seed, per-condition rows behind every
  aggregate, with a data dictionary (also written by `cta dataset`).

Use `--full` for the larger protocol (slower). Runs are deterministic: the same
command reproduces the same numbers.

## Product proof of concept (offline, deterministic)

```
python -m examples.poc
```

A small fleet self-selects tasks through the calibrated, gated bid; the report
shows the allocation, the out-of-scope actions the integrity gate stopped, and
the coordinator cost avoided. No model calls.

## Concurrent claiming under real processes (P3.1)

```
cta concurrency --tasks 50 --workers 1,2,4,8
```

Races several OS processes to claim tasks over the SQLite store and reports the
throughput per worker count and the zero double-claims invariant. No model calls.

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
