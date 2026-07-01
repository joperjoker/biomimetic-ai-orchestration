# Extended Theory and Design Notes

This document expands the theoretical material summarised in `claude.md`. It records the verified reference, a worked example of the Binding Energy calculation, the reliability model, the task lifecycle, the concurrency story, the validation metrics, and the limits of the biological analogy.

## 1. Reference

The framework draws its central intuition from the following study:

> Fitzpatrick JL, Willis C, Devigili A, Young A, Carroll M, Hunter HR, Brison DR. (2020) Chemical signals from eggs facilitate cryptic female choice in humans. Proceedings of the Royal Society B: Biological Sciences, 287(1928): 20200805. DOI: 10.1098/rspb.2020.0805. Published 11 June 2020.

The study reports that human follicular fluid releases chemoattractants that preferentially draw sperm from particular males, and that the effect depends on the specific combination of follicular fluid and sperm. The selection therefore continues after the initial encounter, and it is biased by chemical signalling rather than decided by a single external authority.

## 2. The Binding Energy calculation

Agents rank their fit for a task using:

```
Binding Energy = (S x C) / L
```

- `S` (Task Signal): normalised match between the task scent envelope and the agent domain, in [0, 1].
- `C` (Agent Capability): normalised competence for the required skills, in [0, 1].
- `L` (Latency or compute cost penalty): expected cost of the agent taking the task, strictly positive, floored at a small value (suggested 0.01) so the score stays bounded.

### 2.1 Worked example

Three agents evaluate the same task:

| Agent | S | C | L | Binding Energy |
|-------|-----|------|------|----------------|
| A | 0.90 | 0.80 | 2.00 | (0.90 x 0.80) / 2.00 = 0.360 |
| B | 0.60 | 0.95 | 1.00 | (0.60 x 0.95) / 1.00 = 0.570 |
| C | 0.95 | 0.50 | 0.50 | (0.95 x 0.50) / 0.50 = 0.950 |

Agent C wins. The example shows that a strong signal match combined with low latency can beat raw capability (Agent B has the highest `C` yet loses). This is the intended behaviour: the framework rewards good fit and low cost, not capability alone.

### 2.2 Edge cases and guards

- If `S = 0` (no domain match), Binding Energy is 0, so a mismatched agent never competes.
- If a computed `L` is zero or negative, clamp it to the floor (0.01) before dividing.
- A participation threshold (suggested default 0.2) keeps agents from competing for work where their Binding Energy is negligible, which reduces contention.

### 2.3 Comparability

Binding Energy is comparable between agents evaluating the same task, because they share the same `S` source and the same `L` units for that task. When one agent compares Binding Energy across different tasks to decide what to pursue, the values are relative rather than absolute, so the agent should treat them as a ranking rather than a calibrated quantity.

## 3. Reliability and the Rejection Gate

The Rejection Gate admits an agent only when its reliability is at or above an acceptance threshold and its proposed action passes integrity checks.

### 3.1 Reliability score

Reliability is a Laplace smoothed success ratio over a sliding window of recent attempts:

```
R = (s + 1) / (n + 2)
```

- `s`: successful attempts within the window.
- `n`: total attempts within the window (suggested window size 20).
- The smoothing terms (+1 and +2) keep a new agent near 0.5 rather than at an undefined or extreme value.

### 3.2 Acceptance threshold

The acceptance threshold (suggested default 0.6) is the minimum reliability for admission. An agent below the threshold is deflected, the task returns to the pool, and the agent's capability may be reduced.

### 3.3 Coupling reliability into Binding Energy

One option worth considering is to fold reliability into the capability term, so that an unreliable agent both scores lower when competing and is more likely to be deflected at the gate:

```
C_effective = C_base x R
```

This keeps a single reliability signal driving both selection and admission.

## 4. Task lifecycle

```
CREATED
   |
   v
ADVERTISED  <-----------------------+
   |                                |
   v                                |
CLAIMED                             |
   |                                |
   v                                |
[REJECTION GATE]                    |
   |          \                     |
admitted     deflected ------> RE_ADVERTISED
   |                                ^
   v                                |
EXECUTING                           |
   |        \                       |
COMPLETED   FAILED ----------------+
```

A deflected or failed task returns to the pool for re-advertisement. A completed task updates the winning agent's reliability and capability scores.

## 5. Concurrency and the claim step

Selection is decentralised, yet two agents can compute the highest Binding Energy for the same task at the same moment. The claim step therefore needs a consistency primitive so that exactly one agent wins. A practical option is an atomic compare-and-swap on the task state in a shared coordination store: the first agent to move the task from ADVERTISED to CLAIMED wins, and the others observe the change and move on.

This means the orchestrator is not removed entirely. It becomes a thin coordination layer (a consistent log or a compare-and-swap store) rather than a central workload assigner. Acknowledging this honestly matters: the scaling claim of the framework rests on the orchestrator doing far less work per task, not on its complete absence.

## 6. Validation metrics

The Validator measures the framework against quantities, not impressions:

- Allocation latency: time from advertisement to a successful claim.
- Match quality: mean Binding Energy of winning agents.
- Deflection rate: fraction of claims the gate rejects, with false deflection tracked separately.
- Load fairness: distribution of completed tasks across agents (for example a Gini coefficient).
- Starvation: maximum time any task waits in the pool.
- Scaling: allocation latency plotted against agent and task population size, which is the central hypothesis to test against a centralised baseline.

## 7. Limits of the biological analogy

The biology is a source of design intuition, not a literal specification. Several points of divergence are worth stating plainly:

- Cryptic female choice operates after mating within a single female, whereas tasks here are many and short lived.
- Sperm do not compute their own fitness, whereas agents actively calculate their own Binding Energy. The framework adds agent side computation that has no biological counterpart.
- The zona pellucida is a passive chemical barrier, whereas the Rejection Gate is an active evaluator that reasons about reliability and scope.

These divergences are acceptable. The value of the analogy is the principle of decentralised, signal led selection, not a one to one mechanical correspondence.

## 8. Licence decision

The project is licensed under the Apache License, Version 2.0. The reasoning: a permissive licence with an explicit patent grant suits a research framework that may describe novel methods, because it offers contributors and adopters clarity on patent rights. A simpler permissive licence (for example MIT) was weighed as an alternative where minimal terms are preferred, and was set aside because it lacks the explicit patent grant. The full text is in the `LICENSE` file at the repository root.
