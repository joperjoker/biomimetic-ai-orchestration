# Biomimetic AI Orchestration

A decentralised multi-agent orchestration framework inspired by evolutionary biology. The project replaces the conventional top-down central scheduler with a distributed, signal-driven model in which tasks advertise themselves and agents self-select the work they are best suited to perform.

## Motivation

Current multi-agent frameworks tend to rely on a deterministic central orchestrator that assigns workloads from the top down. As the agent population grows, that orchestrator becomes a scaling bottleneck and a single point of failure. This repository validates a decentralised alternative drawn from reproductive biology, specifically the model of cryptic female choice described by Fitzpatrick and colleagues (2020).

In place of a central manager, every task emits a semantic metadata envelope (referred to throughout as the scent). Distributed agents observe these envelopes and autonomously calculate their own compatibility before competing for the work. A pre-execution sandbox (the Rejection Gate) screens candidates so that agents with degraded reliability are deflected before they can gain write access.

## Core Concepts

### The Scent (Task Signal Envelope)

Each task publishes a structured metadata envelope describing its requirements, priority, and resource expectations. Agents read the envelope rather than waiting for an assignment, which removes the central dispatch step.

### Agent Binding Energy

Agents rank their fit for a task using the Agent Binding Energy equation:

```
Binding Energy = (S x C) / L
```

Where:

- `S` is the Task Signal strength (how strongly the task envelope matches the agent's declared domain).
- `C` is the Agent Capability score (the agent's competence for the required skills).
- `L` is the Latency or compute cost penalty (the expected time and resource cost of the agent taking the task).

A higher Binding Energy indicates a stronger affinity. Among the agents that clear the activation barrier (see below), the highest Binding Energy wins, which produces an emergent allocation without a central scheduler. A worked example and the edge-case guards are set out in `docs/theory.md`.

### Selection in stages

Matching runs in two stages, then a trust gate, so each step answers one question:

- Eligibility (binary): can the agent do the task at all (domain, permissions, tools)? If no agent qualifies, the task is infeasible given the present agents.
- Activation energy (graded): among eligible agents, does the best Binding Energy reach the task barrier `Ea`? If none clears it, the task is stalled and waits for a better matched agent or a catalyst.
- Trust (the Rejection Gate): is the winning agent reliable and its action in scope?

The default firing rule is a deterministic threshold (`BE >= Ea`), with an optional Arrhenius temperature variant for exploration. The two-stage model, the worked cases (infeasible and stalled), and the firing rule are set out in `docs/theory.md` section 3.

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
            | Binding Energy and  | <-- BE = (S x C) / L and attempt only
            | activation (BE>=Ea) |     when BE reaches Ea; none clears -> stalled
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

## Repository Layout

```
.
├── README.md            Project overview (this file)
├── claude.md            Master context and theoretical blueprint for autonomous loops
├── CONTRIBUTING.md      Operating protocol, style constraints, and local checks
├── CHANGELOG.md         Notable changes
├── pyproject.toml       Project manifest and tooling configuration (provisional)
├── src/
│   ├── signals/         Task scent envelope generation and parsing
│   ├── agents/          Agent definitions, capability scoring, Binding Energy logic
│   ├── gates/           Rejection Gate sandbox and reliability scoring
│   └── orchestrator/    Decentralised coordination and event loop
├── tests/               Validation suites (including the foundation guard)
├── docs/                Extended theory, worked example, glossary, and references
└── .github/             Continuous integration and repository configuration
```

## Getting started

The project targets Python 3.11 or later. This is a confirmed decision recorded in `claude.md`.

```
python -m pip install -e ".[dev]"
ruff check .
pytest
```

At this stage the modules are not yet implemented, so the test suite contains a foundation guard that checks the structure, the key documents, and the style constraints.

## Status

This foundation run establishes the directory layout, the persistent documentation, the project hygiene files, and continuous integration. Implementation of the signal, agent, gate, and orchestrator modules follows in subsequent development phases, tracked in `claude.md`.

## Considerations for Future Work

The following points are offered as considerations rather than fixed directives:

- A reference implementation of the Binding Energy calculation could be paired with a deterministic test fixture so that scoring behaviour stays reproducible across changes.
- The Rejection Gate could expose its reliability threshold as a tunable parameter, which would let operators trade throughput against safety.
- A small simulation harness might help observe emergent allocation patterns before the framework is connected to live agents.

## References

Fitzpatrick JL, Willis C, Devigili A, Young A, Carroll M, Hunter HR, Brison DR. (2020) Chemical signals from eggs facilitate cryptic female choice in humans. Proceedings of the Royal Society B: Biological Sciences, 287(1928): 20200805. DOI: [10.1098/rspb.2020.0805](https://doi.org/10.1098/rspb.2020.0805).

## Licence

Licensed under the Apache License, Version 2.0. See the [`LICENSE`](LICENSE) file for the full text. The reasoning behind the choice is recorded in `docs/theory.md`.
