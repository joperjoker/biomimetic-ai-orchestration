# Extended Theory and Design Notes

This document expands the theoretical material summarised in `claude.md`. It records the verified reference, the Binding Energy calculation, the two-stage selection model with activation energy, the reliability model, the task lifecycle, the concurrency story, the validation metrics, and the limits of the analogies.

## 1. Reference

The framework draws its central intuition from the following study:

> Fitzpatrick JL, Willis C, Devigili A, Young A, Carroll M, Hunter HR, Brison DR. (2020) Chemical signals from eggs facilitate cryptic female choice in humans. Proceedings of the Royal Society B: Biological Sciences, 287(1928): 20200805. DOI: 10.1098/rspb.2020.0805. Published 11 June 2020.

The study reports that human follicular fluid releases chemoattractants that preferentially draw sperm from particular males, and that the effect depends on the specific combination of follicular fluid and sperm. The selection therefore continues after the initial encounter, and it is biased by chemical signalling rather than decided by a single external authority.

The activation barrier draws on a second source, the response threshold model of division of labour in social insects (Bonabeau, Theraulaz, and Deneubourg, 1996), in which an individual engages a task only when the task stimulus exceeds its threshold. This gives the barrier an established precedent that has since been operationalised in swarm robotics. The complete formal model, with numbered equations, is set out in `docs/paper.md` section 2.2.

## 2. The Binding Energy calculation

Eligible agents (section 3) rank their fit for a task using:

```
Binding Energy = (S x C) / L
```

- `S` (Task Signal): normalised match between the task scent envelope and the agent domain, in [0, 1].
- `C` (Agent Capability): normalised competence for the required skills, in [0, 1].
- `L` (Latency or compute cost penalty): expected cost of the agent taking the task, strictly positive, floored at a small value (suggested 0.01) so the score stays bounded. `L` is a normalised relative cost with a typical value near 1, so `B` typically lies in [0, 1] and the absolute barrier `Ea` in [0, 1] is meaningful; a near-zero-cost agent simply clears the barrier.

In the canonical model, `S` is an embedding cosine between the task need and the agent capability, and capability is coupled with reliability as the effective capability `C_tilde = C x R` (section 4.3), so the score used is `B = S x C_tilde / max(L, 0.01)`. See `docs/paper.md` section 2.2, equations E3 to E6.

### 2.1 Worked example

Three eligible agents evaluate the same task (the example uses base capability, that is `R = 1`, so `C_tilde = C`):

| Agent | S | C | L | Binding Energy |
|-------|-----|------|------|----------------|
| A | 0.90 | 0.80 | 2.00 | (0.90 x 0.80) / 2.00 = 0.360 |
| B | 0.60 | 0.95 | 1.00 | (0.60 x 0.95) / 1.00 = 0.570 |
| C | 0.95 | 0.50 | 0.50 | (0.95 x 0.50) / 0.50 = 0.950 |

Agent C wins. The example shows that a strong signal match combined with low latency can beat raw capability (Agent B has the highest `C` yet loses). This is the intended behaviour: the framework rewards good fit and low cost, not capability alone.

### 2.2 Edge cases and guards

- If a computed `L` is zero or negative, clamp it to the floor (0.01) before dividing.
- Whether an agent competes at all is decided by the two-stage model in section 3, not inside this equation: an ineligible agent is filtered out first, and an eligible agent competes only when its Binding Energy clears the activation energy `Ea`.

### 2.3 Comparability

Binding Energy is comparable between agents evaluating the same task, because they share the same `S` source and the same `L` units for that task. When one agent compares Binding Energy across different tasks to decide what to pursue, the values are relative rather than absolute, so the agent should treat them as a ranking rather than a calibrated quantity.

## 3. Two-stage selection and activation energy

Matching is decided in two stages, followed by the trust gate in section 4. The two stages answer separate questions, so they do not overlap: eligibility asks whether an agent can do the task at all, and activation asks whether the match is strong enough to fire.

### 3.1 Stage one: the Eligibility Filter (binary)

Each agent first applies a categorical yes or no test for a task. It is cheap, so it runs first and shrinks the candidate set. An agent is eligible only when all of the following hold:

- Capability domain: the agent covers the domain the task requires.
- Scope and permissions: the agent is permitted to act within the task's declared scope.
- Tools: the agent holds the tools or resources the task names as required.

If no agent in the present population is eligible, the task is infeasible given that population. This is the frame's account of work that cannot be done: it is a property of the task scope set against the agents that exist, not a scoring artefact. An infeasible task is flagged and can be revisited if the population changes.

### 3.2 Stage two: Activation Energy

Among eligible agents, a match must overcome a barrier before the task proceeds, the activation energy `Ea`. An eligible agent attempts to claim only when:

```
BE >= Ea
```

- `Ea` travels in the task envelope and is task-specific: demanding or higher-risk tasks set a higher barrier, routine tasks set a lower one.
- The default `Ea` is 0.2 when a task does not specify one.
- If eligible agents exist but none clears `Ea`, the task is stalled: it waits for a better matched agent or for a catalyst, rather than being executed by a poor match. Stalled is distinct from infeasible.

### 3.3 Firing rule: deterministic default with an Arrhenius extension

Default (deterministic threshold): a task fires when the best eligible Binding Energy reaches `Ea`. This is simple, reproducible, and faithful to the idea of reaching a barrier.

Extension (Arrhenius, optional): firing is probabilistic, echoing the Arrhenius relation where the fraction of collisions with enough energy scales with `exp(-Ea / (k T))`. Here the chance that an eligible agent fires rises smoothly with its Binding Energy relative to the barrier, governed by a system temperature `T`:

```
p(fire) = 1                        when BE >= Ea
p(fire) = exp(-(Ea - BE) / T)      when BE < Ea
```

A higher `T` lets more marginal matches fire (exploration), a lower `T` admits only strong matches (exploitation). As `T` approaches zero, this reduces to the deterministic threshold. A small illustration with `Ea = 0.20`:

| BE | Ea - BE | p(fire), T = 0.05 | p(fire), T = 0.20 |
|------|---------|-------------------|-------------------|
| 0.22 | below 0 | 1.00 | 1.00 |
| 0.18 | 0.02 | 0.67 | 0.90 |
| 0.10 | 0.10 | 0.14 | 0.61 |
| 0.05 | 0.15 | 0.05 | 0.47 |

The table shows the knob: at low temperature a match just under the barrier rarely fires, and at higher temperature the system is more willing to try a weaker match. Writing the activation drive as `Delta = BE - Ea`, this firing rule is `p(fire) = min(1, exp(Delta / T))`, which is equation E8 in `docs/paper.md` section 2.2.

### 3.4 Considerations: catalyst and annealing

- Catalyst: supporting context, a tool, a cache, or a helper agent can lower the effective `Ea` for a task, letting a marginal match fire. This mirrors a catalyst lowering the activation energy of a reaction without being consumed by it. It is a future extension, offered as a consideration.
- Annealing: a task that stalls for too long could have its `Ea` reduced gradually so it does not starve. This connects to the starvation metric in section 7 and is also offered as a consideration.

### 3.5 Quality feedback and self-assessment

Two further elements close the loop and keep the model honest about its weakest assumption, that an agent can score itself.

- Independent quality: the realised outcome of a task is drawn from a ground-truth quality function that does not depend on the agent's own estimate. An attempt counts as a success when the realised quality clears a minimum, and that success or failure updates the reliability `R`. This lets quality be measured against something other than the affinity score that drove selection.
- Self-assessment noise: agents act on noisy, possibly biased estimates of their own `S`, `C`, and `L`. Selection uses the estimated Binding Energy, while outcomes use the ground truth. Sweeping the bias and noise shows how sensitive the framework is to miscalibrated agents. These elements are equations E12 and E13 in `docs/paper.md` section 2.2.

## 4. Reliability and the Rejection Gate

The Rejection Gate is the third stage, and it decides trust rather than fit: the two selection stages choose who should take a task, and the gate decides whether that agent can be trusted to write. It admits an agent only when its reliability is at or above an acceptance threshold and its proposed action passes integrity checks.

### 4.1 Reliability score

Reliability is a Laplace smoothed success ratio over a sliding window of recent attempts:

```
R = (s + 1) / (n + 2)
```

- `s`: successful attempts within the window.
- `n`: total attempts within the window (suggested window size 20).
- The smoothing terms (+1 and +2) keep a new agent near 0.5 rather than at an undefined or extreme value.

### 4.2 Acceptance threshold

The acceptance threshold (suggested default 0.6) is the minimum reliability for admission. An agent below the threshold is deflected, the task returns to the pool, and the agent's capability may be reduced.

### 4.3 Coupling reliability into Binding Energy

By default the model folds reliability into the capability term, so that an unreliable agent both scores lower when competing and is more likely to be deflected at the gate:

```
C_tilde = C x R
```

This keeps a single reliability signal driving both selection and admission (equation E5). An ablation that disables the coupling (using base capability `C` directly) is available for analysis.

## 5. Task lifecycle

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

INFEASIBLE means no eligible agent exists in the present population, and it can return to ADVERTISED if the population changes. STALLED means eligible agents exist but none cleared `Ea`, and it is re-advertised, optionally with `Ea` annealing. A deflected or failed task returns to the pool. A completed task updates the winning agent's reliability and capability.

## 6. Concurrency and the claim step

Selection is decentralised, yet two agents can compute the highest Binding Energy for the same task at the same moment. The claim step therefore needs a consistency primitive so that exactly one agent wins. A practical option is an atomic compare-and-swap on the task state in a shared coordination store: the first agent to move the task from ADVERTISED to CLAIMED wins, and the others observe the change and move on.

This means the orchestrator is not removed entirely. It becomes a thin coordination layer (a consistent log or a compare-and-swap store) rather than a central workload assigner. Acknowledging this honestly matters: the scaling claim of the framework rests on the orchestrator doing far less work per task, not on its complete absence.

## 7. Validation metrics

The Validator measures the framework against quantities, not impressions:

- Allocation latency: time from advertisement to a successful claim.
- Coordinator work: claim attempts per allocated task, distinct from total evaluation work and communication.
- Match quality: realised quality `Q` of winning agents, with mean Binding Energy reported alongside as the proxy.
- Infeasible rate: fraction of tasks with no eligible agent.
- Stall rate: fraction of tasks that are eligible but fail to clear `Ea` on first advertisement.
- Deflection rate: fraction of claims the gate rejects, with false deflection tracked separately.
- Load fairness: distribution of completed tasks across agents (for example a Gini coefficient).
- Starvation: maximum time any task waits in the pool.
- Scaling: coordinator work and allocation latency plotted against agent and task population size, which is the central hypothesis to test against a centralised baseline.

The complete metric set, with operational definitions and the measurement map, is in `docs/paper.md` section 2.4 and `docs/architecture.md` section 6.

## 8. Limits of the analogies

The biology and the chemistry are sources of design intuition, not literal specifications. Several points of divergence are worth stating plainly:

- Cryptic female choice operates after mating within a single female, whereas tasks here are many and short lived.
- Sperm do not compute their own fitness, whereas agents actively calculate their own Binding Energy. The framework adds agent side computation that has no biological counterpart.
- The zona pellucida is a passive chemical barrier, whereas the Rejection Gate is an active evaluator that reasons about reliability and scope.
- In physical chemistry, binding energy (a measure of stability, thermodynamics) and activation energy (a kinetic barrier) sit on different axes and are not compared directly. The framework compares `BE` with `Ea` on purpose as a modelling device, so the relation `BE >= Ea` is a design choice rather than a physical identity.
- The eligibility filter corresponds loosely to reactant compatibility (the right reactive sites must be present) rather than to any single equation.

These divergences are acceptable. The value of the analogies is the principle of decentralised, signal led selection with a barrier to firing, not a one to one mechanical correspondence.

## 9. Licence decision

The project is licensed under the Apache License, Version 2.0. The reasoning: a permissive licence with an explicit patent grant suits a research framework that may describe novel methods, because it offers contributors and adopters clarity on patent rights. A simpler permissive licence (for example MIT) was weighed as an alternative where minimal terms are preferred, and was set aside because it lacks the explicit patent grant. The full text is in the `LICENSE` file at the repository root.
