# Changelog

All notable changes to this project are recorded in this file. The format follows the spirit of Keep a Changelog, and the project aims to follow semantic versioning once a first release is cut.

## [Unreleased]

### Added

- Foundational workspace: directory layout separating signals, agents, gates, and the orchestrator.
- `README.md` with motivation, core concepts, an architecture diagram, and a worked Binding Energy example.
- `claude.md` as persistent master context: theory, equations, lifecycle, concurrency model, and validation criteria.
- `docs/theory.md` with the verified reference, a worked example, the reliability model, and the limits of the biological analogy.
- `docs/glossary.md` mapping biological terms to their engineering counterparts.
- Project hygiene: `.gitignore`, `pyproject.toml`, `CONTRIBUTING.md`, and a continuous integration workflow.
- Foundation guard test suite that checks structure, key documents, and the style constraints.
- Apache License 2.0 (`LICENSE`), and the confirmed language decision (Python 3.11 or later).
- Two-stage selection frame: a binary eligibility filter followed by an activation-energy barrier (`BE >= Ea`), with a deterministic threshold default and an optional Arrhenius temperature extension, plus the distinct infeasible and stalled outcomes.
- Research draft (`docs/paper.md`): introduction (problem, prior art, contributions, research questions) and methodology (design, formal model, baseline, variables and metrics, procedure, analysis, validity and threats), with verified references.
