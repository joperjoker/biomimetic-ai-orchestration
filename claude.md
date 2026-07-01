# claude.md: Master Context for Biomimetic AI Orchestration

This file is the persistent memory for the biomimetic-ai-orchestration project. It captures the full theoretical background, the governing equations, the architectural blueprint, and the operating protocol so that subsequent research and development loops can execute autonomously without the originating prompt being re-supplied. Read this file at the start of every session before planning work. The extended theory, the worked example, and the references live in `docs/theory.md`, and the biology to engineering mapping lives in `docs/glossary.md`.

## 1. Mission

Validate a decentralised multi-agent orchestration framework that removes the central scheduler. Tasks advertise themselves through a semantic metadata envelope (the scent), distributed agents self-select work by calculating their own affinity, and a pre-execution sandbox (the Rejection Gate) screens candidates before they gain write access. The biological reference is cryptic female choice, drawn from Fitzpatrick and colleagues (2020), cited in full in section 9.

Research North Star (do not lose sight of this): the one claim under test is that decentralised, signal-driven self-selection relieves the central-orchestrator bottleneck while holding match quality and safety. The biomimicry (cryptic female choice for signal-driven choice, the response threshold model for the activation barrier, the zona pellucida for the trust gate) is the design source, not the goal. Every addition should serve that claim or be marked as a consideration.

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

This is the foundational departure from conventional orchestration: choice is distributed and signal-driven, not centrally dictated. The limits of this analogy are recorded in `docs/theory.md` section 8, and should be kept in mind so the biology guides intuition without being treated as a literal specification.

The activation barrier (section 3.5) draws on a second source, the response threshold model of division of labour in social insects (Bonabeau, Theraulaz, and Deneubourg, 1996), in which an individual engages a task only when the stimulus exceeds its threshold. The complete formal model, named Chemotactic Task Allocation, is set out with numbered equations in `docs/paper.md` section 2.2.

### 3.2 Selection in two stages, then a trust gate

Matching a task to an agent is decided in two stages, followed by a distinct trust gate. Each step answers a different question, so the stages do not overlap:

1. Eligibility (binary): can this agent do the task in principle? See section 3.3.
2. Activation (graded): among eligible agents, is the best Binding Energy at or above the task barrier? See sections 3.4 and 3.5.
3. Trust (the Rejection Gate): is the winning agent reliable and its action safe? See section 3.6.

```
[Eligibility Filter]  ->  [Binding Energy + Activation]  ->  [Rejection Gate]
   Can it, at all?          Is the match strong enough?         Is it trustworthy?
   binary yes or no         BE >= Ea                            reliability + integrity
```

This structure borrows a second chemistry idea alongside binding energy: activation energy, the barrier a reaction must overcome before it proceeds. A useful consequence is that the framework can express work that cannot be done: a task with no eligible agent is infeasible, and a task with eligible agents but none clearing the barrier is stalled. These two outcomes are distinct and are handled separately (sections 3.3, 3.5, and 4.3).

### 3.3 Stage one: the Eligibility Filter (binary)

Before any affinity is computed, each agent applies a binary eligibility test for the task. The test is categorical, not graded, and it is cheap so it can run first and shrink the candidate set. An agent is eligible only when all of the following hold:

- Capability domain: the agent covers the capability domain the task requires.
- Scope and permissions: the agent is permitted to act within the task's declared scope.
- Tools: the agent holds the tools or resources the task names as required.

If no agent in the present population is eligible, the task is infeasible given that population. It is flagged rather than retried blindly, and it can be revisited if the agent population changes. The eligibility test corresponds to reactant compatibility in chemistry (the right reactive sites must be present), not to the strength of the eventual bond.

### 3.4 Agent Binding Energy

Eligible agents quantify their affinity for a task using the Agent Binding Energy equation:

```
Binding Energy = (S x C) / L
```

Variables:

- `S` (Task Signal): the strength of the match between the task's scent envelope and the agent's declared domain. Normalised to [0, 1].
- `C` (Agent Capability): the agent's competence for the specific skills the task requires. Normalised to [0, 1].
- `L` (Latency or compute cost penalty): the expected time and resource cost of the agent undertaking the task. Strictly greater than zero, floored at a small value (suggested 0.01) to keep the score bounded.

Interpretation: Binding Energy rises with stronger signal match and higher capability, and falls as cost rises. Among the agents that clear the activation barrier (section 3.5), the highest Binding Energy wins. A worked numerical example is given in `docs/theory.md` section 2.1.

Decided rules (defaults, revisable):

- Latency floor: clamp `L` to 0.01 if a computed value is zero or negative.
- Tie breaker: when two agents compute equal Binding Energy, the agent with the lower `L` wins; if still tied, the lower agent identifier wins. This keeps outcomes deterministic and reproducible.
- Capability coupling: capability may be scaled by reliability as `C_effective = C_base x R` (see section 3.6), so an unreliable agent both competes less strongly and is more likely to be deflected.

### 3.5 Stage two: Activation Energy

Binding Energy alone does not commit an agent to a task. As in a chemical reaction, the match must first overcome a barrier, the activation energy `Ea`. An eligible agent attempts to claim a task only when its Binding Energy is at or above the task's `Ea`:

```
the reaction fires when   BE >= Ea
```

- `Ea` is carried by the task envelope and is task-specific: demanding or higher-risk tasks set a higher barrier, routine tasks set a lower one.
- Default `Ea` is 0.2 when a task does not specify one. This replaces the earlier flat participation threshold with a task-specific barrier.
- If eligible agents exist but none clears `Ea`, the task is stalled: it waits for a better matched agent, or for a catalyst, rather than being executed by a poor match.

Firing rule (decided: threshold default, with an Arrhenius extension):

- Default (deterministic threshold): a task fires when the best eligible Binding Energy reaches `Ea`. Simple and reproducible.
- Extension (Arrhenius, optional): firing is probabilistic, with the chance of firing rising as Binding Energy approaches and exceeds `Ea`, governed by a system temperature `T`. A higher `T` admits more marginal matches (exploration), a lower `T` admits only strong matches (exploitation). The deterministic threshold is the limiting case of this extension at low temperature. Details and a probability table are in `docs/theory.md` section 3.

Considerations:

- Catalyst: supporting context, a tool, a cache, or a helper agent can lower the effective `Ea` for a task, letting a marginal match fire. This is a future extension, not a first-phase requirement.
- Annealing: a task that stalls for too long could have its `Ea` lowered gradually so it does not starve. This ties directly to the starvation metric in section 6.

### 3.6 The Rejection Gate (Zona Pellucida Analogue)

The Rejection Gate is the distinct third stage: it decides trust, not fit. Where the eligibility filter and the activation barrier decide whether an agent should take a task, the gate decides whether the chosen agent can be trusted to write. In biology, the zona pellucida is the glycoprotein layer surrounding the egg that controls which sperm may penetrate, providing a selective barrier. The Rejection Gate is the computational analogue: a pre-execution sandbox that every agent must pass before it gains write access.

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
├── agents/       Agent definitions, eligibility test, capability scoring (C), Binding Energy, activation
├── gates/        Rejection Gate sandbox, reliability scoring, integrity checks
└── orchestrator/ Decentralised event loop, task pool, advertisement and re-advertisement
```

### 4.2 Data Flow

1. A task is created and the signals module produces its scent envelope, including its eligibility requirements and its activation energy `Ea`.
2. The envelope is published to the task pool in the orchestrator.
3. Stage one: each agent applies the binary eligibility test. Ineligible agents ignore the task. If no agent is eligible, the task is infeasible.
4. Each eligible agent computes Binding Energy = (S x C) / L.
5. Stage two: an eligible agent attempts to claim only when its Binding Energy is at or above the task's `Ea`. If no eligible agent clears `Ea`, the task is stalled and returns to the pool.
6. Among the agents attempting to claim, the highest Binding Energy wins via the atomic claim (with the deterministic tie breaker from section 3.4).
7. Stage three: the claiming agent presents its proposed action to the Rejection Gate.
8. The gate admits or deflects. Admitted agents execute with write access; deflected and failed tasks return to the pool.
9. Outcomes update agent capability and reliability scores, closing the feedback loop.

### 4.3 Task Lifecycle

```
CREATED -> ADVERTISED -> [ELIGIBILITY FILTER]
                              |            \
                          eligible       none eligible -> INFEASIBLE
                              |
                              v
                  [ACTIVATION: best eligible BE >= Ea ?]
                              |            \
                            fires        below Ea -> STALLED -> RE_ADVERTISED -> ADVERTISED
                              |
                              v
                     CLAIMED (atomic) -> [REJECTION GATE]
                              |               |          \
                              |           admitted    deflected -> RE_ADVERTISED -> ADVERTISED
                              v
                        EXECUTING -> COMPLETED
                              |
                        EXECUTING -> FAILED -> RE_ADVERTISED -> ADVERTISED
```

Notes:

- INFEASIBLE means no eligible agent exists in the present population. It is flagged and can return to ADVERTISED if the population changes.
- STALLED means eligible agents exist but none cleared `Ea`. It is re-advertised, and annealing of `Ea` (section 3.5) can be applied to avoid starvation.
- A deflected or failed task returns to the pool. A completed task updates the winning agent's reliability and capability.

### 4.4 Concurrency and the Claim Step

Selection is decentralised, yet two agents can compute the highest Binding Energy for the same task at the same moment, so the claim step needs a consistency primitive that lets exactly one agent win. The decided approach is an atomic compare-and-swap on the task state in a shared coordination store: the first agent to move the task from ADVERTISED to CLAIMED wins, and the others observe the change and move on.

This means the orchestrator is a thin coordination layer (a consistent log or a compare-and-swap store), not a central workload assigner. The scaling claim of the framework rests on the orchestrator doing far less work per task, not on its complete absence. This is recorded honestly so future phases test the right hypothesis.

### 4.5 Scent Envelope (suggested schema)

A task envelope is expected to carry at minimum:

- `task_id`: unique identifier.
- `domain`: the capability domain required, used to compute `S`.
- `eligibility`: the required capabilities, permissions, and tools that the binary filter (section 3.3) checks.
- `activation_energy`: the barrier `Ea` a match must clear to fire (section 3.5), default 0.2.
- `priority`: relative urgency.
- `expected_cost`: a hint contributing to each agent's `L` estimate.
- `scope`: the declared boundary the Rejection Gate uses for integrity checks.

The concrete serialisation (for example JSON with a validation schema) is left to the Engineer in the implementation phase.

### 4.6 Experimental Architecture (evaluation)

The framework is evaluated in two modes that share one core, so results are comparable and every metric is recoverable. A simulation mode (Python, synthetic agents) provides scale and determinism for the scaling curves. A real-swarm pilot (a small set of Claude Code subagents over a Supabase Postgres coordination store) provides ecological validity, including real self-assessment, latency, cost, and quality. The atomic claim is a real conditional update in Postgres (`UPDATE tasks SET status='CLAIMED', claimed_by=$a WHERE id=$t AND status='ADVERTISED' RETURNING id`), so the decentralised coordination is measured rather than assumed. All activity is written to an append-only event log, so each metric is a query. The central baseline (Hungarian and greedy) uses the same shared scoring module, which isolates coordination as the only variable. The full component design, controls, metric-to-measurement map, and evaluation protocol are in `docs/architecture.md`.

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
- claude.md holds the full theory (cryptic female choice, the two-stage selection, Binding Energy, activation energy, Rejection Gate) so future loops need no external context.
- Each subsequent phase leaves the repository in a committed, reproducible state.

Quantitative metrics for the implementation phase (measured against a centralised baseline):

- Allocation latency: time from advertisement to a successful claim.
- Match quality: mean Binding Energy of winning agents.
- Infeasible rate: fraction of tasks with no eligible agent.
- Stall rate: fraction of tasks that are eligible but fail to clear `Ea` on first advertisement.
- Deflection rate: fraction of claims the gate rejects, with false deflection tracked separately.
- Load fairness: distribution of completed tasks across agents (for example a Gini coefficient).
- Starvation: maximum time any task waits in the pool.
- Scaling: allocation latency against agent and task population size, which is the central hypothesis.

## 7. Decisions and Assumptions Recorded

- Language and runtime: Python 3.11 or later. Confirmed. If ever changed, update `pyproject.toml` and the CI workflow.
- Selection is a two-stage process (eligibility filter, then activation energy), followed by the Rejection Gate as a distinct trust stage.
- Eligibility is a binary test over capability domain, scope and permissions, and required tools. No eligible agent means the task is infeasible.
- Activation energy `Ea` is task-specific, default 0.2, and replaces the earlier flat participation threshold. Firing uses a deterministic threshold by default, with an optional Arrhenius temperature extension.
- The working directory itself is the project root, so no nested project folder was created.
- Capability and signal values are normalised to [0, 1].
- The latency penalty `L` is strictly positive with a floor of 0.01.
- Acceptance threshold 0.6 and reliability window 20, both revisable.
- The formal model is named Chemotactic Task Allocation (CTA) and is specified in `docs/paper.md` section 2.2.
- Effective capability couples reliability into affinity by default: `C_effective = C_base x R`.
- Evaluation uses an independent ground-truth quality model (not the affinity score) to judge outcomes, and models self-assessment as noisy and possibly biased, so calibration can be studied.
- Evaluation is dual-mode: a Python simulation for scale, and a real-swarm pilot of Claude Code subagents over Supabase Postgres for ecological validity. See section 4.6 and `docs/architecture.md`.
- Pilot stack (assumed, revisable): Claude Code subagents as the swarm, Supabase Postgres as the task pool, atomic-claim store, event log, and reliability store.
- Pilot task type (assumed, revisable): software micro-tasks in this repository, giving an objective ground-truth quality (test pass fraction).
- Licence: Apache-2.0 (confirmed). The full text is in the `LICENSE` file, and the reasoning is in `docs/theory.md` section 9.

## 8. Open Items for Future Phases

- Define the concrete scent envelope serialisation and a validation schema, including the `eligibility` and `activation_energy` fields.
- Implement the binary eligibility filter, including the infeasible outcome when no agent qualifies.
- Implement and unit test the Binding Energy calculation with a deterministic fixture.
- Implement the activation gate: the deterministic threshold first, then the optional Arrhenius temperature variant, including the stalled outcome.
- Implement the Rejection Gate with a configurable reliability threshold and integrity checks.
- Implement the atomic claim primitive in the orchestrator.
- Explore the catalyst and `Ea` annealing extensions once the base pipeline is measured.
- Build a simulation harness to observe emergent allocation and to measure the metrics in section 6 against a centralised baseline.
- Create the Supabase schema (tasks, agents, events, attempts) and the atomic-claim statement.
- Build the real-swarm pilot: Claude Code subagents that self-assess, claim, pass the gate, and execute scoped software micro-tasks in isolated git worktrees.
- Build the analysis layer that computes the metric-to-measurement map in `docs/architecture.md` from the event log.
- Follow the phased build in `docs/roadmap.md`: the agent harnesses, the Auto-Researcher loop (a Karpathy-style propose, run, evaluate, keep-or-revert loop kept on a leash by the Rejection Gate), and the repository shaped as the public report. Not yet started.

## 9. References

Bonabeau E, Theraulaz G, Deneubourg J-L. (1996) Quantitative study of the fixed threshold model for the regulation of division of labour in insect societies. Proceedings of the Royal Society of London B: Biological Sciences, 263(1376): 1565-1569. DOI: 10.1098/rspb.1996.0229.

Fitzpatrick JL, Willis C, Devigili A, Young A, Carroll M, Hunter HR, Brison DR. (2020) Chemical signals from eggs facilitate cryptic female choice in humans. Proceedings of the Royal Society B: Biological Sciences, 287(1928): 20200805. DOI: 10.1098/rspb.2020.0805. Published 11 June 2020.

The complete research reference list is in `docs/paper.md`.
