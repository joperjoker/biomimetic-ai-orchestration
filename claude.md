# claude.md: Master Context for Biomimetic AI Orchestration

This file is the persistent memory for the biomimetic-ai-orchestration project. It captures the full theoretical background, the governing equations, the architectural blueprint, and the operating protocol so that subsequent research and development loops can execute autonomously without the originating prompt being re-supplied. Read this file at the start of every session before planning work. The extended theory, the worked example, and the references live in `docs/theory.md`, and the biology to engineering mapping lives in `docs/glossary.md`.

## 1. Mission

Validate a decentralised multi-agent orchestration framework that removes the central scheduler. Tasks advertise themselves through a semantic metadata envelope (the scent), distributed agents self-select work by calculating their own affinity, and a pre-execution sandbox (the Rejection Gate) screens candidates before they gain write access. The biological reference is cryptic female choice, drawn from Fitzpatrick and colleagues (2020), cited in full in section 9.

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

This is the foundational departure from conventional orchestration: choice is distributed and signal-driven, not centrally dictated. The limits of this analogy are recorded in `docs/theory.md` section 7, and should be kept in mind so the biology guides intuition without being treated as a literal specification.

### 3.2 Agent Binding Energy

Agents quantify their affinity for a task using the Agent Binding Energy equation:

```
Binding Energy = (S x C) / L
```

Variables:

- `S` (Task Signal): the strength of the match between the task's scent envelope and the agent's declared domain. Normalised to [0, 1].
- `C` (Agent Capability): the agent's competence for the specific skills the task requires. Normalised to [0, 1].
- `L` (Latency or compute cost penalty): the expected time and resource cost of the agent undertaking the task. Strictly greater than zero, floored at a small value (suggested 0.01) to keep the score bounded.

Interpretation: Binding Energy rises with stronger signal match and higher capability, and falls as cost rises. Agents pursue tasks where their Binding Energy is highest. The emergent effect is that capable, well matched, low cost agents win work without any central assignment step. A worked numerical example is given in `docs/theory.md` section 2.1.

Decided rules (defaults, revisable):

- Latency floor: clamp `L` to 0.01 if a computed value is zero or negative.
- Participation threshold: an agent competes only when its Binding Energy is at or above 0.2, which reduces contention for poorly matched work.
- Tie breaker: when two agents compute equal Binding Energy, the agent with the lower `L` wins; if still tied, the lower agent identifier wins. This keeps outcomes deterministic and reproducible.
- Capability coupling: capability may be scaled by reliability as `C_effective = C_base x R` (see section 3.3), so an unreliable agent both competes less strongly and is more likely to be deflected.

### 3.3 The Rejection Gate (Zona Pellucida Analogue)

In biology, the zona pellucida is the glycoprotein layer surrounding the egg that controls which sperm may penetrate, providing a selective barrier. The Rejection Gate is the computational analogue: a pre-execution sandbox that every agent must pass before it gains write access.

Mechanics:

1. An agent that has won a task on Binding Energy presents its proposed action to the gate.
2. The gate evaluates the agent's recent reliability score and the integrity of the proposed action (for example, whether it stays within declared scope).
3. If the reliability score is at or above the acceptance threshold and the action passes integrity checks, the agent is admitted and granted write access for that task.
4. If the agent's reliability has degraded below the threshold, it is deflected. The task returns to the available pool for re-advertisement, and the deflected agent's capability score may be further reduced.

Design intent: the gate protects shared state from agents that have become unreliable, mirroring how the zona pellucida prevents unsuitable or excess gametes from fertilising the egg. The gate is the security boundary of the framework; agents never write directly without passing it.

Reliability scoring (decided defaults, revisable):

- Reliability is a Laplace smoothed success ratio over a sliding window: `R = (s + 1) / (n + 2)`, where `s` is successful attempts and `n` is total attempts in the window (suggested window size 20). A new agent therefore starts near 0.5.
- Acceptance threshold: an agent is admitted only when `R` is at or above 0.6, and deflected otherwise.
- Recovery path: a deflected agent could be offered a probationary low risk task rather than being permanently excluded. This is a consideration for the implementation phase.

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
4. The highest affinity agent claims the task (with the deterministic tie breaker from section 3.2).
5. The claiming agent presents its proposed action to the Rejection Gate.
6. The gate admits or deflects. Admitted agents execute with write access; deflected tasks return to the pool.
7. Outcomes update agent capability and reliability scores, closing the feedback loop.

### 4.3 Task Lifecycle

```
CREATED -> ADVERTISED -> CLAIMED -> [REJECTION GATE]
                                       |          \
                                   admitted     deflected -> RE_ADVERTISED -> ADVERTISED
                                       |
                                   EXECUTING -> COMPLETED
                                       |
                                   EXECUTING -> FAILED -> RE_ADVERTISED -> ADVERTISED
```

A deflected or failed task returns to the pool. A completed task updates the winning agent's reliability and capability.

### 4.4 Concurrency and the Claim Step

Selection is decentralised, yet two agents can compute the highest Binding Energy for the same task at the same moment, so the claim step needs a consistency primitive that lets exactly one agent win. The decided approach is an atomic compare-and-swap on the task state in a shared coordination store: the first agent to move the task from ADVERTISED to CLAIMED wins, and the others observe the change and move on.

This means the orchestrator is a thin coordination layer (a consistent log or a compare-and-swap store), not a central workload assigner. The scaling claim of the framework rests on the orchestrator doing far less work per task, not on its complete absence. This is recorded honestly so future phases test the right hypothesis.

### 4.5 Scent Envelope (suggested schema)

A task envelope is expected to carry at minimum:

- `task_id`: unique identifier.
- `domain`: the capability domain required, used to compute `S`.
- `priority`: relative urgency.
- `expected_cost`: a hint contributing to each agent's `L` estimate.
- `scope`: the declared boundary the Rejection Gate uses for integrity checks.

The concrete serialisation (for example JSON with a validation schema) is left to the Engineer in the implementation phase.

## 5. Operating Protocol for Autonomous Loops

### 5.1 Execution Loop

For every action follow this sequence: Plan, Analyse Plan, Evaluate Plan, Revise Plan, Execute Plan, Verify Execution, then Loop to Plan again if the objective is not met.

### 5.2 Loop Constraints

- Limit internal validation loops to a maximum of three iterations to prevent stalling.
- If perfection is unreachable within three iterations, synthesize the most stable version and flag the limitations explicitly.

### 5.3 Autonomy

- Do not halt to ask for clarification. When data is missing, make the highest probability architectural decision and record the assumption in this file or in the relevant document.

### 5.4 Stylistic Constraints (apply to all artifacts)

- Do not use the clause separating dash. Use commas, colons, or parentheses instead. This rule is enforced automatically by the foundation test suite, which scans tracked Markdown for dash variants.
- Avoid puffery words such as pivotal, tapestry, and delve.
- Maintain professional British English in prompts, documentation, and code comments.
- Frame recommendations as considerations rather than assertive commands.

## 6. Success Criteria and Validation Metrics (Strategist and Validator)

Qualitative criteria:

- The workspace contains a clear directory layout that separates signals, agents, gates, and the orchestrator.
- README.md explains the motivation and core concepts for a newcomer.
- claude.md holds the full theory (cryptic female choice, Binding Energy, Rejection Gate) so future loops need no external context.
- Each subsequent phase leaves the repository in a committed, reproducible state.

Quantitative metrics for the implementation phase (measured against a centralised baseline):

- Allocation latency: time from advertisement to a successful claim.
- Match quality: mean Binding Energy of winning agents.
- Deflection rate: fraction of claims the gate rejects, with false deflection tracked separately.
- Load fairness: distribution of completed tasks across agents (for example a Gini coefficient).
- Starvation: maximum time any task waits in the pool.
- Scaling: allocation latency against agent and task population size, which is the central hypothesis.

## 7. Decisions and Assumptions Recorded

- Language and runtime: Python 3.11 or later. Confirmed. If ever changed, update `pyproject.toml` and the CI workflow.
- The working directory itself is the project root, so no nested project folder was created.
- Capability and signal values are normalised to [0, 1].
- The latency penalty `L` is strictly positive with a floor of 0.01.
- Default participation threshold 0.2, acceptance threshold 0.6, reliability window 20, all revisable.
- Licence: Apache-2.0 (confirmed). The full text is in the `LICENSE` file, and the reasoning is in `docs/theory.md` section 8.

## 8. Open Items for Future Phases

- Define the concrete scent envelope serialisation and a validation schema.
- Implement and unit test the Binding Energy calculation with a deterministic fixture.
- Implement the Rejection Gate with a configurable reliability threshold and integrity checks.
- Implement the atomic claim primitive in the orchestrator.
- Build a simulation harness to observe emergent allocation and to measure the metrics in section 6 against a centralised baseline.

## 9. References

Fitzpatrick JL, Willis C, Devigili A, Young A, Carroll M, Hunter HR, Brison DR. (2020) Chemical signals from eggs facilitate cryptic female choice in humans. Proceedings of the Royal Society B: Biological Sciences, 287(1928): 20200805. DOI: 10.1098/rspb.2020.0805. Published 11 June 2020.
