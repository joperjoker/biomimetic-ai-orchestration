# Decentralised Multi-Agent Task Allocation via Signal-Driven Selection

A biomimetic framework inspired by cryptic female choice. This document holds the research introduction and methodology. It is self-contained on the essentials and refers to `claude.md` and `docs/theory.md` for the full model.

## 1. Introduction

Multi-agent systems increasingly coordinate large numbers of autonomous agents over many concurrent tasks. A common pattern places a central orchestrator in charge of assigning work from the top down. This pattern is simple to reason about, yet it concentrates two costs at one point: the coordinator must evaluate candidates for every task, and its throughput caps the throughput of the whole system. As the agent and task counts grow, the central node becomes a scaling bottleneck and a single point of failure.

Decentralised alternatives have a long record. The Contract Net Protocol (Smith, 1980) distributes control through an announce, bid, and award exchange, although the award decision for each task still passes through a manager. Market and auction based allocation, surveyed and formalised by Gerkey and Matarić (2004), casts allocation as an optimisation problem and clarifies where decentralised methods trade optimality for scalability. Stigmergic methods such as ant colony optimisation (Dorigo, Maniezzo, and Colorni, 1996) coordinate indirectly through signals left in a shared environment, with no central assigner at all. These results establish that decentralised allocation is viable. Three gaps remain visible across much of this work: the award step is often still centralised per task, a trust or reliability screen before execution is rarely integrated, and there is seldom a principled account of tasks that cannot be done given the agents present.

This project studies a decentralised framework that addresses those three gaps, drawing its selection principle from reproductive biology. In cryptic female choice, selection continues after the initial encounter and is biased by chemical signalling rather than decided by a single authority (Fitzpatrick et al., 2020). Translated to computation: each task emits a semantic metadata envelope (the scent), and distributed agents self-select by computing an affinity score, the Binding Energy `(S x C) / L`. Selection proceeds in two stages, a binary eligibility filter and then an activation energy barrier `Ea` that a match must clear to fire, followed by a distinct trust stage, the Rejection Gate, modelled on the zona pellucida. The biology and chemistry are used as design intuition, not as literal specifications, and the limits of both analogies are recorded in `docs/theory.md` section 8.

Contributions:

1. A decentralised allocation framework in which tasks advertise semantic envelopes and agents self-select by affinity, reducing per-task coordination to an atomic claim rather than a central assignment.
2. A two-stage selection model that separates categorical capability (eligibility) from graded affinity (activation energy), and that yields a principled distinction between infeasible tasks (no eligible agent) and stalled tasks (eligible agents present, none clearing `Ea`).
3. A reliability trust gate that screens degraded agents before they gain write access.
4. An evaluation methodology that compares the framework against a centralised baseline on both scaling and match quality, with operational metrics.

Research questions:

- RQ1: Does signal-driven self-selection reduce per-task coordination cost and allocation latency, relative to a central assigner, as the population grows?
- RQ2: Does it do so without materially degrading match quality?
- RQ3: Does the two-stage model correctly separate infeasible from stalled tasks?
- RQ4: Does the Rejection Gate preserve completion integrity when some agents are unreliable?

Scope and non-goals: this is a simulation study, not a live deployment. The atomic claim assumes a single logical coordination store providing compare-and-swap, so the framework reduces central work rather than removing it entirely (discussed in `docs/theory.md` section 6). The security model is limited to reliability scoring and scope integrity, and does not address adversarial agents beyond degraded reliability.

## 2. Methodology

### 2.1 Research design

The study is a comparative, controlled simulation. Two systems are measured under identical task and agent populations: the decentralised framework and a centralised baseline. The scoring function (Binding Energy) is shared by both systems, so the only difference is how allocation is coordinated. This isolates the effect of decentralisation. Population size is varied to test the scaling hypothesis, and each configuration is run for many seeded replications to support interval estimates.

### 2.2 Formal model (summary)

- Task: carries a scent envelope with a required domain, eligibility requirements, an activation energy `Ea` (default 0.2), a priority, an expected cost, and a declared scope.
- Agent: carries a capability profile, permissions, tools, and a reliability history.
- Signal `S`, Capability `C` in [0, 1]; Latency penalty `L` strictly positive, floored at 0.01.
- Affinity: `Binding Energy = (S x C) / L`.
- Stage one (eligibility): a binary predicate over domain, permissions, and tools. No eligible agent means the task is infeasible.
- Stage two (activation): an eligible agent competes only when `BE >= Ea`. No eligible agent clearing `Ea` means the task is stalled. The firing rule is a deterministic threshold by default, with an optional Arrhenius variant governed by a temperature `T` (`docs/theory.md` section 3).
- Reliability: `R = (s + 1) / (n + 2)` over a sliding window; admission at the Rejection Gate requires `R` at or above the acceptance threshold (default 0.6) and an in-scope action.

### 2.3 Baseline

The centralised baseline is a single scheduler that, each round, assigns tasks to agents using the same Binding Energy scores. Two variants are used: an optimal one-to-one assignment by the Hungarian algorithm (Kuhn, 1955) maximising total match quality, and a greedy highest-affinity assigner. Comparing against both bounds the framework between the optimal and the naive centralised case.

### 2.4 Variables and metrics

Independent variables: number of agents `N`, number of tasks `M`, task arrival rate, the distribution of `Ea`, temperature `T`, the reliability acceptance threshold, and the injected fraction of unreliable agents.

Dependent variables, with operational definitions:

- Allocation latency: wall-clock or simulated time from advertisement to a successful claim.
- Coordination cost: messages or compare-and-swap operations per allocated task.
- Match quality: mean Binding Energy of winning agents, and, where a synthetic ground-truth quality exists, the realised task outcome.
- Infeasible rate and stall rate: fractions of tasks in each outcome, checked against the generator's ground truth.
- Deflection rate: fraction of claims the gate rejects, with false deflection tracked separately.
- Load fairness: distribution of completed tasks across agents (Gini coefficient).
- Starvation: maximum time any task waits in the pool.
- Throughput: completed tasks per unit time.
- Scaling curves: allocation latency and coordination cost as functions of `N`.

### 2.5 Procedure

Agent and task populations are drawn from controlled distributions with fixed random seeds. Each run includes a warm-up period that is excluded from measurement. Each configuration is repeated across at least thirty seeds to estimate confidence intervals. Raw event logs are retained so that every derived metric can be recomputed from source. The deterministic firing rule is used for exact replication, and any Arrhenius runs record their seeds and temperature.

### 2.6 Analysis

Results are reported as means with 95 per cent confidence intervals. Systems are compared per metric. For scaling, growth of coordination cost and latency against `N` is fitted and compared between systems. Given that latency distributions are typically skewed, non-parametric tests (for example the Mann-Whitney U test) are preferred, and effect sizes are reported alongside p-values. Hypotheses and acceptance margins are fixed in advance to reduce the risk of post-hoc selection.

Hypotheses:

- H1: coordination cost per task and allocation latency grow more slowly with `N` for the framework than for the centralised baseline.
- H2: mean match quality is within a pre-registered margin of the Hungarian optimal baseline.
- H3: the framework labels a task infeasible exactly when no eligible agent exists, and stalled exactly when eligible agents exist but none clears `Ea`.
- H4: under injected unreliability, the framework with the Rejection Gate achieves a higher successful-completion and integrity rate than an ablation without the gate.

### 2.7 Validity and threats

- Internal validity: the shared scoring function and fixed seeds isolate the coordination effect. Threat: implementation bias between the two systems. Mitigation: a single shared scoring module, code review, and open configurations.
- External validity: simulated timings and failures may not match live agents. Threat: limited generalisation. Mitigation: parameter sweeps, sensitivity analysis, and an explicit statement of the limitation.
- Construct validity: Binding Energy is a proxy for allocation quality. Threat: the proxy may not track real outcomes. Mitigation: synthetic tasks with a known ground-truth quality, measured alongside the proxy.
- Reproducibility: code, seeds, and configurations are versioned, and continuous integration runs the deterministic path, so reported runs can be reproduced exactly.

### 2.8 Ethical considerations

The study uses synthetic data in simulation, with no human subjects. The biological source is used only as a source of design intuition, and no claim is made about human reproduction.

## References

Dorigo, M., Maniezzo, V., & Colorni, A. (1996) Ant System: optimization by a colony of cooperating agents. IEEE Transactions on Systems, Man, and Cybernetics, Part B, 26(1), 29-41.

Fitzpatrick, J.L., Willis, C., Devigili, A., Young, A., Carroll, M., Hunter, H.R., & Brison, D.R. (2020) Chemical signals from eggs facilitate cryptic female choice in humans. Proceedings of the Royal Society B: Biological Sciences, 287(1928), 20200805. DOI: 10.1098/rspb.2020.0805.

Gerkey, B.P., & Matarić, M.J. (2004) A formal analysis and taxonomy of task allocation in multi-robot systems. The International Journal of Robotics Research, 23(9), 939-954.

Kuhn, H.W. (1955) The Hungarian method for the assignment problem. Naval Research Logistics Quarterly, 2(1), 83-97.

Smith, R.G. (1980) The Contract Net Protocol: high-level communication and control in a distributed problem solver. IEEE Transactions on Computers, C-29(12), 1104-1113.
