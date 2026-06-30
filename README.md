# Biomimetic AI Orchestration

A decentralised multi-agent orchestration framework inspired by evolutionary biology. The project replaces the conventional top-down central scheduler with a distributed, signal-driven model in which tasks advertise themselves and agents self-select the work they are best suited to perform.

## Motivation

Current multi-agent frameworks tend to rely on a deterministic central orchestrator that assigns workloads from the top down. As the agent population grows, that orchestrator becomes a scaling bottleneck and a single point of failure. This repository validates a decentralised alternative drawn from reproductive biology, specifically the model of cryptic female choice described in the 2020 study "Chemical signals from eggs facilitate cryptic female choice in humans".

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

A higher Binding Energy indicates a stronger affinity. Agents pursue tasks where their Binding Energy is highest, which produces an emergent allocation without a central scheduler.

### The Rejection Gate (Zona Pellucida Analogue)

Before any agent gains write access, it must pass the Rejection Gate, a pre-execution sandbox modelled on the biological zona pellucida. The gate evaluates the candidate's recent reliability and the integrity of its proposed action. Agents whose reliability has degraded below the acceptance threshold are deflected, which protects shared state from unreliable actors.

## Repository Layout

```
.
├── README.md            Project overview (this file)
├── claude.md            Master context and theoretical blueprint for autonomous loops
├── src/
│   ├── signals/         Task scent envelope generation and parsing
│   ├── agents/          Agent definitions, capability scoring, Binding Energy logic
│   ├── gates/           Rejection Gate sandbox and reliability scoring
│   └── orchestrator/    Decentralised coordination and event loop
├── tests/               Validation suites
├── docs/                Extended design notes and research references
└── .github/             Continuous integration and repository configuration
```

## Status

This run establishes the foundational workspace: the directory layout and the persistent documentation. Implementation of the signal, agent, gate, and orchestrator modules follows in subsequent development phases.

## Considerations for Future Work

The following points are offered as considerations rather than fixed directives:

- A reference implementation of the Binding Energy calculation could be paired with a deterministic test fixture so that scoring behaviour stays reproducible across changes.
- The Rejection Gate could expose its reliability threshold as a tunable parameter, which would let operators trade throughput against safety.
- A small simulation harness might help observe emergent allocation patterns before the framework is connected to live agents.

## Licence

To be determined in a later phase.
