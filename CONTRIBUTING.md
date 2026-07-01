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

- `src/signals/`: scent envelope schema and signal strength scoring (S).
- `src/agents/`: agent definitions, capability scoring (C), and Binding Energy.
- `src/gates/`: the Rejection Gate, reliability scoring, and integrity checks.
- `src/orchestrator/`: the decentralised event loop and task pool.
- `docs/`: extended theory, the worked example, the glossary, and references.
- `tests/`: validation suites, including the foundation guard.
