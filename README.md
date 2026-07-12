# Biomimetic AI Orchestration

A decentralised multi-agent orchestration framework inspired by evolutionary biology. The project replaces the conventional top-down central scheduler with a distributed, signal-driven model in which tasks advertise themselves and agents self-select the work they are best suited to perform.

## Motivation

Current multi-agent frameworks tend to rely on a deterministic central orchestrator that assigns workloads from the top down. As the agent population grows, that orchestrator becomes a scaling bottleneck and a single point of failure. This repository validates a decentralised alternative drawn from reproductive biology, specifically the model of cryptic female choice described by Fitzpatrick and colleagues (2020).

In place of a central manager, every task emits a semantic metadata envelope (referred to throughout as the scent). Distributed agents observe these envelopes and autonomously calculate their own compatibility before competing for the work. A pre-execution sandbox (the Rejection Gate) screens candidates so that agents with degraded reliability are deflected before they can gain write access.

## Core Concepts

### The Scent (Task Signal Envelope)

Each task publishes a structured metadata envelope describing its requirements, priority, and resource expectations. Agents read the envelope rather than waiting for an assignment, which removes the central dispatch step.

### Agent Binding Energy

Among the agents willing to take a task, the winner is chosen by the Binding Energy:

```
Binding Energy  B = (c x C_tilde) / L
```

Where:

- `c` is the agent's compatibility with the task, a self-scored match in [0, 1] that the task wrapper computes from the agent's role, skills, and prompt against the task's advertised contract. Activation is on this compatibility (`c >= Ea`).
- `C_tilde` is the effective capability, the agent's competence discounted by its observable reliability (the track record `R`), so a confident but historically unreliable agent is ranked down.
- `L` is the normalised cost penalty (the expected time and resource cost of the agent taking the task).

A higher Binding Energy indicates a stronger affinity. The activation barrier is compared against the compatibility `c`; among the agents that clear the barrier, the highest Binding Energy wins, which produces an emergent allocation without a central scheduler. Because the bid is the agent's own self-report and language-model agents are miscalibrated about their fit, weighting by the track record `R` is what makes self-selection robust to that miscalibration (the study's central result). A worked example and the edge-case guards are in `docs/theory.md`, and every quantity is defined operationally in `docs/measures.md`.

### Selection in stages

Matching runs in two stages, then a trust gate, so each step answers one question:

- Eligibility (binary): can the agent do the task at all (domain, permissions, tools)? If no agent qualifies, the task is infeasible given the present agents.
- Activation energy (graded): among eligible agents, does the best compatibility `c` reach the task barrier `Ea`? If none clears it, the task is stalled and waits for a better matched agent or a catalyst.
- Trust (the Rejection Gate): is the winning agent reliable and its action in scope?

The default firing rule is a deterministic threshold (`c >= Ea`), with an optional Arrhenius temperature variant for exploration. The two-stage model, the worked cases (infeasible and stalled), and the firing rule are set out in `docs/theory.md` section 3.

### The Rejection Gate (Zona Pellucida Analogue)

Before any agent gains write access, it must pass the Rejection Gate, a pre-execution sandbox modelled on the biological zona pellucida. The gate evaluates the candidate's recent reliability and the integrity of its proposed action. Agents whose reliability has degraded below the acceptance threshold are deflected, which protects shared state from unreliable actors. The reliability formula and the acceptance threshold are defined in `docs/theory.md`.

## Architecture at a glance

```
            +---------------------+
   task --> |   signals (scent)   |  envelope carries domain, eligibility, Ea; scores S
            +----------+----------+
                       |
                       v
            +---------------------+     stage one: keep only agents that can
            | eligibility filter  |     do the task at all (binary yes or no)
            +----------+----------+     no eligible agent -> infeasible
                       |
                       v
            +---------------------+     stage two: eligible agents compute
            | Binding Energy and  | <-- BE = (c x C~) / L, attempt only
            | activation (c>=Ea)  |     when compatibility c reaches Ea; none -> stalled
            +----------+----------+
                       |
                       v
            +---------------------+     highest Binding Energy wins the
            | orchestrator claim  |     atomic claim (thin coordination)
            +----------+----------+
                       |
                       v
            +---------------------+     stage three: admits or deflects on
            |    Rejection Gate   |     reliability and integrity (trust)
            +----------+----------+
                       | admitted (write access granted)
                       v
            +---------------------+
            |    agent executes   |  outcome updates capability and reliability
            +---------------------+
```

The orchestrator is deliberately thin: it provides the consistency needed for a single agent to claim a task, rather than assigning workloads. The two-stage selection, the lifecycle, and the concurrency model are described in `docs/theory.md`.

## Research approach

The framework is evaluated against a centralised baseline in two modes that share one scoring core, so coordination is the only variable. A Python simulation provides scale and the scaling curves, and a small real-swarm pilot of agents competing over a shared coordination store provides ecological validity. Every action is written to an append-only event log, so each metric is a query over that log. The research write-up is in `docs/paper.md`, and the experimental architecture (components, controls, the metric-to-measurement map, and the evaluation protocol) is in `docs/architecture.md`.

## Repository Layout

One paper comes out of this work, in its own self-contained folder:

- **The paper** (`paper1/`): "Scent, Threshold, and Track Record: A Biomimetic
  Framework for Calibration-Robust Multi-Agent LLM Task Allocation" (plain-language
  edition; the technical edition keeps a conventional title). It runs from the
  mechanism through synthetic and real-agent evidence to the deployed router (an
  Agent Client Protocol broker) with a head-to-head and a live vignette. Ships in
  two editions (`main.tex` plain-language, `main_formal.tex` technical). An earlier
  standalone second paper on the deployment was merged in and now lives in
  `archive/paper2/`.

```
.
├── README.md            Project overview (this file)
├── claude.md            Master context and theoretical blueprint for autonomous loops
├── CONTRIBUTING.md      Operating protocol, style constraints, and local checks
├── CHANGELOG.md         Notable changes
├── REPRODUCE.md         How to regenerate every result from seeds
├── pyproject.toml       Project manifest and tooling configuration
├── paper1/              The paper's arXiv package: main.tex (plain-language) and
│                        main_formal.tex (technical), refs.bib, figures, build.sh,
│                        and the reviewer-revision checklist (REVISIONS.md)
├── src/cta/             The framework: scoring, engine, temporal, baselines,
│                        generators, realism, harness, stats, store, cost,
│                        routing, concurrent, dataset, report, dashboard, viz,
│                        cli, pilot, acp (the ACP broker), the wrapper product
│                        (wrappers), headtohead, and the autoresearch loop
├── pilot_tasks/         Live-pilot task suites and analysers: the standard suite,
│                        the expert-tier ladder, the miniquery project, the
│                        head-to-head replay, and the live-broker vignette
├── examples/            Runnable demos: the product proof of concept (poc) and
│                        the wrapper-layer demo (python -m examples.wrapper_demo)
├── results/             Committed run outputs: summary.json, RESULTS.md, figures,
│                        the showcase dashboard, dataset/runs.csv, the real-agent
│                        runs under live_pilot/, and headtohead/ and vignette/
├── tests/               Validation suites (including the foundation guard)
├── docs/                Markdown sources for both papers (paper.md, paper2.md) and
│                        the reference docs: measures, theory, glossary,
│                        architecture, product, live-pilot notes, acp_integration
├── archive/             Process and planning material, not needed to build the
│                        papers or reproduce results: STATUS.md, planning/, runbooks/
└── .github/             Continuous integration and repository configuration
```

## Getting started

The project targets Python 3.11 or later. This is a confirmed decision recorded in `claude.md`.

```
python -m pip install -e ".[dev]"
ruff check .
pytest
```

Reproduce every result, figure and the raw dataset from seeds with one command:

```
cta reproduce-all --out results
```

This runs the pre-registered sweeps across the six conditions (CTA, pull-based,
central greedy, central optimal, central best, central bounded), computes the
statistics, evaluates the hypotheses, and writes `results/summary.json`,
`results/RESULTS.md`, the SVG figures, the dashboard, and the raw per-run dataset
(`results/dataset/runs.csv`). A runnable product demo is `python -m examples.poc`.
See `REPRODUCE.md` for detail.

## Status

The framework is implemented and evaluated end to end, with 127 tests passing and
`ruff` clean. Ten pre-registered hypotheses on synthetic populations (H1 to H10)
are evaluated by `cta reproduce-all`: H1 (scaling), H3, H4 (safety), H5, H7, H8,
H9, and H10 are supported, while H2 and H6 are not supported against the
full-information optimum and are reported honestly. The calibration-robustness
thesis, that miscalibration is the failure mode of self-selection and a
track-record correction recovers it, is the central result.

Two further hypotheses are confirmed on real Claude agents across three model
families (Haiku 4.5, Sonnet 5, Opus 4.8). H11: a **task wrapper**, an explicit
interface contract, lifts a weak model to a frontier model's completion and is the
precondition for independently built pieces to integrate into a working project.
H12: a **calibrated agent wrapper** routes each task to the cheapest model whose
reliability-corrected self-report clears the barrier, holding frontier-level
completion at roughly one fortieth of the always-frontier cost. These two are
extracted as a small product library (`src/cta/wrappers.py`, demo
`python -m examples.wrapper_demo`) and visualised in a results dashboard
(`results/showcase.html`). The real-agent sample is small and the paper marks that
limit throughout. Progress is tracked in `archive/STATUS.md`; the strategy and forward
plan are in `archive/planning/strategy.md` and `archive/planning/next_experiments.md`.

## Considerations for Future Work

The forward plan is in `archive/planning/strategy.md` and `archive/planning/next_experiments.md`. The open
items are the publication track (a formatted submission and a related-work table),
powering the real-agent results to confidence intervals across every cell, a
two-sided real-agent calibration curve (an out-of-distribution or
in-distribution-overconfident model tier), and the full live-swarm allocation over
the concurrent store already validated under real contention. The commercial
framing is in `docs/product.md`.

## References

Fitzpatrick JL, Willis C, Devigili A, Young A, Carroll M, Hunter HR, Brison DR. (2020) Chemical signals from eggs facilitate cryptic female choice in humans. Proceedings of the Royal Society B: Biological Sciences, 287(1928): 20200805. DOI: [10.1098/rspb.2020.0805](https://doi.org/10.1098/rspb.2020.0805).

## Licence

Licensed under the Apache License, Version 2.0. See the [`LICENSE`](LICENSE) file for the full text. The reasoning behind the choice is recorded in `docs/theory.md`.
