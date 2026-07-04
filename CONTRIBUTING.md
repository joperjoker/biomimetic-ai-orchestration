# Contributing

This document records how work proceeds on biomimetic-ai-orchestration so that contributors (human or automated) share one set of conventions. Read `claude.md` first: it holds the theory and the operating protocol that govern all changes.

## Operating protocol

For every change follow this sequence: Plan, Analyse Plan, Evaluate Plan, Revise Plan, Execute Plan, Verify Execution, then loop back to Plan if the objective is not met. Limit internal validation loops to a maximum of three iterations. If a perfect result is unreachable within three iterations, deliver the most stable version and flag the limitations.

## Style constraints (enforced)

These constraints apply to all prose, documentation, and code comments:

- Do not use the clause separating dash. Use commas, colons, or parentheses instead. This rule is checked automatically by the foundation test suite, which scans tracked Markdown for dash variants.
- Avoid puffery words such as pivotal, tapestry, and delve.
- Write in professional British English.
- Frame recommendations as considerations rather than assertive commands.

## Branching and commits

- Develop on a feature branch, never directly on the default branch.
- Write clear, descriptive commit messages that explain the intent of the change.
- Keep each commit focused on a single logical change where practical.

## Local checks

The project targets Python 3.11 or later (a provisional decision recorded in `claude.md`). Before pushing, run:

```
python -m pip install -e ".[dev]"
ruff check .
pytest
```

## Where things live

- `src/cta/`: the framework as one package. Scoring and Binding Energy
  (`scoring.py`), the batch and temporal engines (`engine.py`, `temporal.py`), the
  Rejection Gate (in `scoring.py`/`engine.py`), the coordination store
  (`store.py`), baselines (`baselines.py`), generators and the realistic fleet
  (`generators.py`, `realism.py`), the experiment harness (`harness.py`), statistics
  (`stats.py`), the cost model (`cost.py`), routing (`routing.py`), the dataset
  writer (`dataset.py`), reporting and figures (`report.py`, `dashboard.py`,
  `viz.py`), the CLI (`cli.py`), the pilot seam (`pilot.py`), and the Auto-Researcher
  loop (`autoresearch/`).
- `pilot_tasks/`: the live-pilot coding task suite, scorer, and analyser.
- `examples/poc/`: the runnable product proof of concept.
- `docs/`: the paper, operational measures, theory, glossary, architecture,
  product framing, and the next-experiments plan.
- `results/`: committed run outputs, figures, dashboard, and the raw dataset.
- `tests/`: validation suites, including the foundation guard.
