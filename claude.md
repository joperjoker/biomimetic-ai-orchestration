# claude.md: Master Context for Biomimetic AI Orchestration

This file is the persistent memory for the biomimetic-ai-orchestration project. It captures the full theoretical background, the governing equations, the architectural blueprint, and the operating protocol so that subsequent research and development loops can execute autonomously without the originating prompt being re-supplied. Read this file at the start of every session before planning work.

## 1. Mission

Validate a decentralised multi-agent orchestration framework that removes the central scheduler. Tasks advertise themselves through a semantic metadata envelope (the scent), distributed agents self-select work by calculating their own affinity, and a pre-execution sandbox (the Rejection Gate) screens candidates before they gain write access. The biological reference is cryptic female choice, drawn from the 2020 study "Chemical signals from eggs facilitate cryptic female choice in humans".

## 2. The Consortium (Persona Model)

Work is reasoned through five virtual personas. They are internal reasoning roles, not separate processes:

1. The Strategist (Lead AI Architect): defines system architecture, success criteria, and theoretical risk mitigation.
2. The Biologist (Senior Evolutionary Biology Researcher): translates biological mechanisms (cryptic female choice, the zona pellucida) into computational heuristics.
3. The Engineer (Core AI Software Engineer): produces implementation logic, metadata structures, and directory layout.
4. The Validator (QA and Validation Team): runs testing and verifies output against the Strategist's criteria.
5. The Synthesizer (Expert Academic Writer and DevOps Engineer): formats production artifacts, manages Git, and maintains this documentation.

## 3. Theoretical Background

### 3.1 Cryptic Female Choice

In reproductive biology, cryptic female choice describes a post-mating selection process in which the female reproductive system biases which gametes succeed, rather than that choice being decided by competition alone. The 2020 study found that chemical signals released by human eggs differentially attract sperm, which means selection continues after the initial encounter and is influenced by chemical signalling rather than by a single external decision maker.

The computational translation:

- The egg corresponds to a task. The task releases a chemical signal (the scent envelope) that biases which agents are drawn towards it.
- The sperm correspond to agents. Many agents may approach, but the task's own signal, combined with each agent's fitness, governs which agent succeeds.
- Selection is decentralised and post-advertisement. There is no central authority assigning the match; the match emerges from signalling and affinity.

This is the foundational departure from conventional orchestration: choice is distributed and signal-driven, not centrally dictated.

### 3.2 Agent Binding Energy

Agents quantify their affinity for a task using the Agent Binding Energy equation:

```
Binding Energy = (S x C) / L
```

Variables:

- `S` (Task Signal): the strength of the match between the task's scent envelope and the agent's declared domain. Range suggested as a normalised value in [0, 1], although implementations may scale it.
- `C` (Agent Capability): the agent's competence for the specific skills the task requires. Suggested range [0, 1].
- `L` (Latency or compute cost penalty): the expected time and resource cost of the agent undertaking the task. Strictly greater than zero to avoid division by zero. A larger `L` lowers Binding Energy.

Interpretation: Binding Energy rises with stronger signal match and higher capability, and falls as cost rises. Agents pursue tasks where their Binding Energy is highest. The emergent effect is that capable, well matched, low cost agents win work without any central assignment step.

Implementation notes (considerations):

- `L` should be clamped to a small positive floor (for example 0.01) so that near zero latency does not produce an unbounded score.
- A tie breaking rule may be needed when two agents compute equal Binding Energy. A deterministic rule (for example lowest `L`, then lowest agent identifier) keeps behaviour reproducible.
- Capability `C` may decay with recent failures, which couples this equation to the reliability tracking used by the Rejection Gate.

### 3.3 The Rejection Gate (Zona Pellucida Analogue)

In biology, the zona pellucida is the glycoprotein layer surrounding the egg that controls which sperm may penetrate, providing a selective barrier. The Rejection Gate is the computational analogue: a pre-execution sandbox that every agent must pass before it gains write access.

Mechanics:

1. An agent that has won a task on Binding Energy presents its proposed action to the gate.
2. The gate evaluates the agent's recent reliability score and the integrity of the proposed action (for example, whether it stays within declared scope).
3. If the reliability score is at or above the acceptance threshold and the action passes integrity checks, the agent is admitted and granted write access for that task.
4. If the agent's reliability has degraded below the threshold, it is deflected. The task returns to the available pool for re-advertisement, and the deflected agent's capability score may be further reduced.

Design intent: the gate protects shared state from agents that have become unreliable, mirroring how the zona pellucida prevents unsuitable or excess gametes from fertilising the egg. The gate is the security boundary of the framework; agents never write directly without passing it.

Reliability scoring (considerations):

- Reliability could be a rolling success ratio over a recent window of attempts.
- The acceptance threshold could be configurable so operators can trade throughput against safety.
- Degraded agents could be given a recovery path (for example a probationary low risk task) rather than being permanently excluded.

## 4. Architectural Blueprint

### 4.1 Module Map

```
src/
├── signals/      Scent envelope schema, generation, parsing, signal strength scoring (S)
├── agents/       Agent definitions, capability scoring (C), Binding Energy calculation
├── gates/        Rejection Gate sandbox, reliability scoring, integrity checks
└── orchestrator/ Decentralised event loop, task pool, advertisement and re-advertisement
```

### 4.2 Data Flow

1. A task is created and the signals module produces its scent envelope.
2. The envelope is published to the task pool in the orchestrator.
3. Agents read the pool, each computing Binding Energy = (S x C) / L for relevant envelopes.
4. The highest affinity agent claims the task (with a deterministic tie breaker).
5. The claiming agent presents its proposed action to the Rejection Gate.
6. The gate admits or deflects. Admitted agents execute with write access; deflected tasks return to the pool.
7. Outcomes update agent capability and reliability scores, closing the feedback loop.

### 4.3 Scent Envelope (suggested schema)

A task envelope is expected to carry at minimum:

- `task_id`: unique identifier.
- `domain`: the capability domain required, used to compute `S`.
- `priority`: relative urgency.
- `expected_cost`: a hint contributing to each agent's `L` estimate.
- `scope`: the declared boundary the Rejection Gate uses for integrity checks.

The concrete serialisation (for example JSON) is left to the Engineer in the implementation phase.

## 5. Operating Protocol for Autonomous Loops

### 5.1 Execution Loop

For every action follow this sequence: Plan, Analyse Plan, Evaluate Plan, Revise Plan, Execute Plan, Verify Execution, then Loop to Plan again if the objective is not met.

### 5.2 Loop Constraints

- Limit internal validation loops to a maximum of three iterations to prevent stalling.
- If perfection is unreachable within three iterations, synthesize the most stable version and flag the limitations explicitly.

### 5.3 Autonomy

- Do not halt to ask for clarification. When data is missing, make the highest probability architectural decision and record the assumption in this file or in the relevant document.

### 5.4 Stylistic Constraints (apply to all artifacts)

- Do not use the clause separating dash. Use commas, colons, or parentheses instead.
- Avoid puffery words such as pivotal, tapestry, and delve.
- Maintain professional British English in prompts, documentation, and code comments.
- Frame recommendations as considerations rather than assertive commands.

## 6. Success Criteria (Strategist)

- The workspace contains a clear directory layout that separates signals, agents, gates, and the orchestrator.
- README.md explains the motivation and core concepts for a newcomer.
- claude.md holds the full theory (cryptic female choice, Binding Energy, Rejection Gate) so future loops need no external context.
- Each subsequent phase leaves the repository in a committed, reproducible state.

## 7. Assumptions Recorded This Run

- The working directory itself is the project root, so no nested project folder was created.
- Capability and signal values are assumed normalised to [0, 1] unless an implementation phase decides otherwise.
- The latency penalty `L` is assumed strictly positive with a small floor to keep Binding Energy bounded.
- No language or runtime has been fixed yet; the implementation phase will select one and document it here.

## 8. Open Items for Future Phases

- Choose the implementation language and runtime, then record the choice in this file.
- Define the concrete scent envelope serialisation and a validation schema.
- Implement and unit test the Binding Energy calculation with a deterministic fixture.
- Implement the Rejection Gate with a configurable reliability threshold.
- Build a simulation harness to observe emergent allocation before connecting live agents.
