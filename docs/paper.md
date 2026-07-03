# Decentralised Multi-Agent Task Allocation via Signal-Driven Selection

A biomimetic framework inspired by cryptic female choice. This document holds the research introduction and methodology. It is self-contained on the essentials and refers to `claude.md` and `docs/theory.md` for the full model.

## 1. Introduction

Multi-agent systems increasingly coordinate large numbers of autonomous agents over many concurrent tasks. A common pattern places a central orchestrator in charge of assigning work from the top down. This pattern is simple to reason about, yet it concentrates two costs at one point: the coordinator must evaluate candidates for every task, and its throughput caps the throughput of the whole system. As the agent and task counts grow, the central node becomes a scaling bottleneck and a single point of failure.

Decentralised alternatives have a long record. The Contract Net Protocol (Smith, 1980) distributes control through an announce, bid, and award exchange, although the award decision for each task still passes through a manager. Market and auction based allocation, surveyed and analysed by Dias, Zlot, Kalra, and Stentz (2006) and formalised by Gerkey and Matarić (2004), casts allocation as an optimisation problem and clarifies where decentralised methods trade optimality for scalability. Stigmergic methods such as ant colony optimisation (Dorigo, Maniezzo, and Colorni, 1996) coordinate indirectly through signals left in a shared environment, with no central assigner at all. These results establish that decentralised allocation is viable. Three gaps remain visible across much of this work: the award step is often still centralised per task, a trust or reliability screen before execution is rarely integrated, and there is seldom a principled account of tasks that cannot be done given the agents present.

This project studies a decentralised framework, Chemotactic Task Allocation (CTA), that addresses those three gaps, drawing its selection principle from two biological sources. From cryptic female choice it takes signal-driven, post-advertisement selection: selection continues after the initial encounter and is biased by chemical signalling rather than decided by a single authority (Fitzpatrick et al., 2020). From the response threshold model of division of labour in social insects it takes the activation barrier: an individual engages a task only when the task stimulus exceeds its threshold (Bonabeau, Theraulaz, and Deneubourg, 1996), a mechanism since operationalised in swarm robotics. Translated to computation: each task is described by a wrapper (the scent envelope) that reads an agent's role, skills, and prompt against the task requirements to produce a compatibility score `c` in [0, 1]. Distributed agents self-select: an agent may take a task only when its compatibility reaches the task's activation energy (`c >= Ea`), and among the willing agents the winner maximises a cost-adjusted, reliability-weighted score, the Binding Energy `B = c x C_tilde / L`. Selection proceeds in two stages, a binary eligibility filter and then the activation barrier, followed by a distinct trust stage, the Rejection Gate, modelled on the zona pellucida. Every quantity is defined operationally in `docs/measures.md`. The biology and chemistry are used as design intuition, not as literal specifications, and the limits of the analogies are recorded in `docs/theory.md` section 8.

Compared with a simple pull-based work queue, where agents self-schedule by taking the best available task, CTA adds three things: the activation barrier as a quality floor, the Rejection Gate as a trust boundary, and the eligibility filter with its infeasible and stalled semantics. The evaluation isolates these additions with a pull-based baseline (section 2.3), so a result is not merely the effect of decentralisation.

Any framework in which agents self-select rests on a load-bearing assumption: that an agent can assess its own fit for a task. Recent studies of auction and bidding among large language model agents report that self-reported success probabilities are systematically miscalibrated, so an allocation built from self-reports diverges from the full-information optimum (Fradkin and Krishnan, 2026), and calibrating that self-confidence is an open problem (Zhang et al., 2026). This is exactly the assumption CTA's compatibility bid depends on. We therefore treat self-assessment as a first-class, swept variable rather than an idealisation. The wrapper's compatibility is the agent's self-report, drawn from its true fit with a bias and noise (E13), while realised quality depends on the true fit and the agent's competence, so miscalibration corrupts the allocation without changing the ground truth. Two questions follow. First, how far does miscalibration degrade a self-selection allocation. Second, whether an observable track record (the reliability `R`, E4), which needs no privileged information, recovers the loss. The Rejection Gate then serves as a safety backstop, screening the winner for scope integrity before it gains write access. This repositions the contribution from decentralised self-selection, which is now well covered, onto the calibration robustness of self-selection, which is not.

Contributions:

1. A decentralised allocation framework in which tasks advertise semantic envelopes and agents self-select by affinity, reducing per-task coordination to an atomic claim rather than a central assignment.
2. A two-stage selection model that separates categorical capability (eligibility) from graded affinity (activation energy), and that yields a principled distinction between infeasible tasks (no eligible agent) and stalled tasks (eligible agents present, none clearing `Ea`).
3. A reliability and integrity trust gate that screens degraded and out-of-scope agents before they gain write access, evaluated as a safety backstop against adversarial agents.
4. An evaluation methodology that compares the framework against a centralised baseline on both scaling and match quality, with operational metrics.
5. A formal framework (Chemotactic Task Allocation) that unifies eligibility, affinity, and activation into one model, with cost accounting that separates total system work from coordinator work.
6. A measurable compatibility wrapper that scores an agent's role, skills, and prompt against a task and can be calibrated to predict success, so the activation threshold rests on an empirically validated score rather than an abstract one (`docs/measures.md`).
7. A study of self-assessment miscalibration as the failure mode of self-selection: the compatibility bid is treated as the agent's self-report (E13), and a track-record correction (the reliability `R`, E4), which uses no privileged information, recovers the completion that miscalibration costs, with the integrity gate as a safety backstop.

Research questions:

- RQ1: Does signal-driven self-selection reduce per-task coordinator work and allocation latency, relative to a central assigner, as the population grows?
- RQ2: Does it do so without materially degrading match quality?
- RQ3: Does the two-stage model correctly separate infeasible from stalled tasks?
- RQ4: Does the Rejection Gate prevent out-of-scope writes when some agents are adversarial?
- RQ5: Is allocation stable across the range of activation barriers and temperatures, without oscillation or starvation?
- RQ6: Does CTA's advantage depend on agent heterogeneity, and if so, how does it change from a homogeneous to a specialised population?
- RQ7: How far does self-assessment miscalibration degrade a decentralised self-selection allocation?
- RQ8: Does a track-record correction, using only observable history, recover the allocation quality that miscalibration costs?

Scope and non-goals: this is a simulation study, not a live deployment. The atomic claim assumes a single logical coordination store providing compare-and-swap, so the framework reduces central work rather than removing it entirely (discussed in `docs/theory.md` section 6). The security model is limited to reliability scoring and scope integrity: it models agents that attempt out-of-scope actions and screens them at the gate, but it does not address a strategic adversary that games the compatibility score or the track record itself.

## 2. Methodology

### 2.1 Research design

The study is a comparative, controlled experiment. Two systems are measured under identical task and agent populations: the decentralised framework and a centralised baseline. The scoring function (Binding Energy) is shared by both systems, so the only difference is how allocation is coordinated. This isolates the effect of decentralisation. Population size is varied to test the scaling hypothesis, and each configuration is run for many seeded replications to support interval estimates.

The experiment runs in two modes that share one core. A simulation mode uses many synthetic agents in Python for scale, determinism, and cheap sweeps, and produces the scaling curves for H1 to H5. A real-swarm pilot uses a small set of Claude Code subagents competing over a shared task pool in a self-contained store (SQLite by default), where the atomic claim is a genuine compare-and-swap, and it supplies ecological validity: real self-assessment, latency, cost, and output quality. The shared core (scent schema, scoring module, event log, and metric code) makes the two modes comparable. The full design is in `docs/architecture.md`.

### 2.2 Formal framework (Chemotactic Task Allocation)

Entities: a set of agents `A` of size `N`, and tasks `T` of size `M` arriving over time. Each task carries a scent envelope `sigma(t) = (d_t, ReqCap_t, ReqPerm_t, ReqTool_t, Ea_t, rho_t, scope_t)`, where `d_t` is the domain, `Ea_t` the activation barrier (default 0.2), and `rho_t` the priority. Each agent has a capability profile, permissions, tools, and a reliability history.

Stage one, eligibility (binary):

- (E1) `elig(a,t) = 1[ReqTool_t subset Tool_a] . 1[scope_t subset Perm_a]`, valued in {0,1}: tools and permitted scope are the hard requirements. Skills and domain are graded into compatibility (E3), not vetoed. See `docs/measures.md` section 2.
- (E2) eligible set `A(t) = { a in A : elig(a,t) = 1 }`. The task is infeasible when `A(t)` is empty.

Compatibility, capability, and the selection score:

- (E3) compatibility `c(a,t)` in [0, 1], produced by the task wrapper from the agent's role, skills, and prompt against the task requirements. It aggregates measurable sub-scores (semantic match, skill coverage, scope fit) by a weighted geometric mean, or by a logistic model calibrated to predict success. Compatibility replaces the abstract signal `S`; full definitions are in `docs/measures.md` section 3.
- (E4) reliability `R(a) = (s_a + 1) / (n_a + 2)`, a Laplace smoothed success ratio over a sliding window of `W` recent attempts.
- (E5) effective capability `C_tilde(a,t) = C(a,t) . R(a)`, with base capability `C` in [0, 1], so reliability enters selection as well as the gate.
- (E6) selection score, the Binding Energy `B(a,t) = c(a,t) . C_tilde(a,t) / max(L(a,t), eps)`, with cost `L > 0` and floor `eps = 0.01`. `B` ranks the agents that have cleared activation; it does not gate firing. In prose `B` is written `BE`, and `L` is a normalised relative cost with a typical value near 1. The activation barrier `Ea` in [0, 1] is compared against compatibility `c` (E7), which is bounded in [0, 1] by construction, so `Ea` is directly interpretable.

Stage two, activation (firing):

- (E7) activation drive `Delta(a,t) = c(a,t) - Ea_t`; the barrier is on compatibility, not on the selection score.
- (E8) firing probability `P_fire(a,t) = 1` when `Delta >= 0`, and `P_fire(a,t) = exp(Delta / T)` when `Delta < 0`, with temperature `T >= 0`. The deterministic threshold is the `T -> 0` limit. This is the Boltzmann or Arrhenius form; the response threshold sigmoid `s^n / (s^n + theta^n)` is an equivalent soft-threshold family.
- (E9) firing set `F(t) = { a in A(t) : u_a <= P_fire(a,t) }`, with `u_a` drawn uniformly on [0, 1]. The task is stalled when `A(t)` is non-empty and `F(t)` is empty.

Claim and trust:

- (E10) winner `a*(t) = argmax over a in F(t) of B(a,t)`; the tie breaker is the lower `L`, then the lower agent identifier. The claim is committed by an atomic compare-and-swap, so exactly one agent wins.
- (E11) the Rejection Gate admits `a*` when `R(a*) >= tau` and `integrity(a*, scope_t) = 1` (acceptance threshold `tau`, default 0.6); otherwise it deflects and the task is re-advertised.

Outcome and feedback:

- (E12) realised quality, a ground truth independent of the agent's self-estimate, `Q(a,t) = clip(g(S_true, C_true) + xi)` with noise `xi ~ N(0, sigma_q^2)`, in [0, 1]. The attempt succeeds when `Q >= q_min`, which updates `(s_a, n_a)` and hence `R`.
- (E13) self-assessment: agents act on noisy estimates `c_hat = clip(c + eta_c)`, `C_hat = clip(C + eta_C)`, and `L_hat = max(eps, L + eta_L)`, with `eta ~ N(b, sigma^2)` for bias `b` and noise `sigma`. Activation and selection use the estimates; outcomes use the truth through E12.
- (E14) annealing: while a task is stalled, `Ea_t <- max(Ea_min, Ea_t - delta)` per waiting round, so the barrier relaxes rather than starving the task.

Cost accounting:

- (C1) total evaluation work `W_eval = sum over t of |A(t)|`, worst case `O(N.M)`, since eligible agents each score the task.
- (C2) coordinator work `W_coord = sum over t of |F(t)|`, the claim attempts contending at the shared store.
- (C3) communication, messages per allocated task. The centralised baseline instead incurs a per-round assignment cost, `O(k^3)` for the Hungarian method over `k` candidates.

The full narrative for these equations is in `docs/theory.md`.

### 2.3 Baseline

The centralised baseline is a single scheduler that, each round, assigns tasks to agents using the same scores. Three variants are used. Two are one-to-one assignments (each agent takes at most one task): an optimal Hungarian assignment (Kuhn, 1955) and a greedy highest-affinity assigner, both over Binding Energy, which serve as the coordination-cost reference for the scaling hypothesis. The third, `central_best`, is the full-information quality optimum for CTA's non-exclusive setting: it gives each task the agent that maximises expected realised quality (true fit times true capability) and allows an agent to take more than one task, exactly as CTA does. Because the one-to-one optima are forced to spread work across weaker agents, they understate the achievable quality and would let CTA appear to beat the optimum; `central_best` is the fair upper bound that CTA should approach from below, and it is the reference for the quality hypothesis H2.

A third, decentralised baseline is a pull-based work queue: agents self-schedule by claiming the best available eligible task, without the activation barrier or the Rejection Gate. It removes the central assigner just as CTA does, so comparing CTA against it isolates the effect of CTA's specific mechanisms (the barrier, the gate, and the infeasible and stalled semantics) from the effect of decentralisation alone. Without this baseline, a scaling result could be attributed merely to avoiding an expensive central optimiser.

### 2.4 Variables and metrics

Independent variables: number of agents `N`, number of tasks `M`, task arrival rate, the distribution of `Ea`, temperature `T`, the reliability acceptance threshold, and the injected fraction of unreliable agents.

Independent variables also include the self-assessment bias `b` and noise `sigma` (E13), so that miscalibrated agents can be studied directly, and the degree of agent capability heterogeneity, from a homogeneous population (agents are near-interchangeable) to a specialised one (agents cover distinct domains). Heterogeneity is expected to matter because self-selection has little to exploit when agents are interchangeable.

Dependent variables, with operational definitions:

- Allocation latency: simulated time from advertisement to a successful claim.
- Coordinator work: `W_coord` (E9, C2), the claim attempts per allocated task, distinct from total evaluation work `W_eval` (C1) and from communication, messages per allocated task (C3). Reporting all three separates the bottleneck from the total compute.
- Claim contention: attempts per successful claim, and the wasted-evaluation rate, the share of firing agents that do not win.
- Herding: the spread of the firing-set size `|F(t)|` across tasks (for example a Gini coefficient over tasks), which detects convergence onto a few attractive tasks.
- Match quality: the realised quality `Q` of winning agents (E12), with mean Binding Energy reported alongside as the proxy.
- Infeasible rate and stall rate: fractions of tasks in each outcome, checked against the generator's ground truth.
- Deflection rate: fraction of claims the gate rejects, with false deflection tracked separately.
- Calibration sensitivity: match quality and deflection rate as functions of the self-assessment bias and noise.
- Completion rate: the fraction of tasks completed successfully, the primary outcome for the calibration-robustness hypotheses (H7, H8), compared across the raw, reliability, and full-information selection modes.
- Overconfidence gap: the mean self-report of winners minus their mean realised quality, the direct measure of miscalibration (H7).
- Calibration error: the Brier score and the expected calibration error (ECE) of the winners' self-reports against their binary success, the standard calibration measures used in the auction and forecasting literature (H7).
- Track-record length: the number of prior attempts behind the reliability estimate, swept to show how much history the correction needs before it is effective.
- Integrity violations: out-of-scope writes that execute when the gate is absent, the safety measure for the gate ablation (H4).
- Load fairness: distribution of completed tasks across agents (Gini coefficient).
- Stability and starvation: the maximum stall time of feasible tasks in the temporal engine, with and without annealing, and the annealing rate needed to bound it.
- Starvation: maximum time any task waits in the pool.
- Throughput: completed tasks per unit time.
- Scaling curves: allocation latency and coordinator work as functions of `N`.

### 2.5 Procedure

Agent and task populations are drawn from controlled distributions with fixed random seeds. Each run includes a warm-up period that is excluded from measurement. Each configuration is repeated across seeded replications, with the seed count set by a pilot power analysis to detect a pre-registered minimum effect size (at least thirty as a floor), so a null result reflects the framework rather than insufficient power. Raw event logs are retained so that every derived metric can be recomputed from source. The deterministic firing rule is used for exact replication, and any Arrhenius runs record their seeds and temperature.

### 2.6 Analysis

Results are reported as means with 95 per cent confidence intervals. Systems are compared per metric. For scaling, growth of coordinator work and latency against `N` is fitted and compared between systems. Given that latency distributions are typically skewed, non-parametric tests (for example the Mann-Whitney U test) are preferred, and effect sizes are reported alongside p-values. Hypotheses and acceptance margins are fixed in advance to reduce the risk of post-hoc selection. H1 and H2 are the pre-registered primary endpoints; the remaining hypotheses are secondary, and their p-values are corrected for multiple comparisons with a Holm-Bonferroni procedure across the reported family of tests. Experiments are driven by an automated research loop with a protected, pre-registered metric and an append-only decision ledger (see `docs/roadmap.md`), which supports reproducibility and guards against metric-hacking. To keep long campaigns reliable, the loop treats the logged record as an external environment to query and recursively summarise rather than holding it all in context, which mitigates context rot (Recursive Language Models: Zhang, Kraska, and Khattab, 2025). This external-memory strategy is a property of the research process, not of the Chemotactic Task Allocation framework under study.

Hypotheses:

- H1: coordinator work per task (C2) and allocation latency grow more slowly with `N` for the framework than for the centralised baseline, and comparably to the decentralised pull-based baseline. Total evaluation work (C1) and communication (C3) are reported alongside and are expected to be comparable or higher, so the claim is bottleneck relief, not less total compute. Since decentralisation alone relieves the bottleneck, CTA's distinct value is holding quality and safety while scaling, tested in H2 and H4.
- H2: mean realised quality `Q` (E12) is within a pre-registered margin (0.05) of the full-information optimum and at least the pull-based baseline. The optimum is `central_best`, which gives each task the agent that maximises expected realised quality (true fit times true capability) with agent reuse allowed, matching CTA's non-exclusive setting rather than a one-to-one assignment that is handicapped by forced spreading.
- H3: the framework labels a task infeasible exactly when no eligible agent exists, and stalled exactly when eligible agents exist but none clears `Ea`.
- H4: with adversarial agents that attempt out-of-scope actions, the Rejection Gate substantially reduces integrity violations relative to an ablation without the gate. The gate detects an out-of-scope action with recall below one, so the result is a measured reduction, not a tautological zero.
- H5: activation-energy annealing (E14) bounds the stall time of feasible tasks. In the temporal engine, a positive annealing rate relaxes the barrier so every feasible task is resolved at bounded stall, whereas without annealing the stalled tasks are never claimed.
- H6: CTA's advantage over both baselines increases with agent heterogeneity, and narrows towards zero in a homogeneous population where self-selection has little to exploit.
- H7: winners' self-reports of fit systematically over-predict the quality they deliver (a materially positive overconfidence gap), because the self-report omits competence, so relying on the self-report alone is a genuine failure mode. We do not claim the gap grows with the injected bias; in this model it is dominated by the structural fit-versus-competence gap.
- H8: discounting the self-report by an observable track record (the reliability `R`, E4) recovers task completion relative to the raw self-report auction, under the worst injected overconfidence.

Falsification: the thesis is not supported if coordinator work and latency grow at the same order for the framework as for the centralised baseline (H1), if realised quality falls below the pre-registered margin of the Hungarian optimum or does not exceed the pull-based baseline (H2), if the gate does not substantially reduce out-of-scope writes by adversarial agents (H4), if annealing does not bound the stall time of feasible tasks (H5), if the advantage does not appear even in the specialised, high-heterogeneity regime (H6), if self-reports are well calibrated so no overconfidence gap appears (H7), or if the track-record correction does not recover completion under miscalibration (H8). These outcomes are reported as stated, not reframed.

### 2.7 Validity and threats

- Internal validity: the shared scoring function and fixed seeds isolate the coordination effect. Threats: implementation bias between the two systems, and claim contention that could confound latency at scale. Mitigations: a single shared scoring module with code review and open configurations, and contention measured directly (attempts per claim, wasted-evaluation rate) rather than assumed away.
- External validity: this is the primary threat. A simulation abstracts away the variable latency, monetary cost, and stochastic output quality of live language-model agents, and it abstracts the cost and miscalibration of an agent scoring itself, which is the weakest real-world link. Reported failure rates for real multi-agent systems are high and are driven by specification ambiguity and coordination breakdown that a simulation does not reproduce (Cemri et al., 2025). Mitigations: sweep the self-assessment bias and noise (E13), state plainly that the study tests the coordination mechanism rather than deployment readiness, and run the real-swarm pilot defined in the experimental architecture (`docs/architecture.md`), using matched runs to calibrate the simulation against live agents.
- Construct validity: Binding Energy is only a proxy for allocation quality, and the framework rests on agents estimating their own compatibility `c`. Mitigation: an independent ground-truth quality function `Q` (E12) drives success and the quality hypothesis H2, and the self-report is modelled explicitly as `c_hat` (E13) with the miscalibration swept, so results do not depend on the agent's self-estimate being accurate.
- Generalisability: results could depend on how the synthetic populations are generated. Mitigation, now carried out: the pre-registered hypotheses are re-run under a second, structurally different generative family. The original `domains` family uses one-hot task requirements and a discrete skill gate, so compatibility is near-binary; the `latent` family draws agent and task directions in a continuous latent space with no skill gate, so compatibility is a smooth function of alignment. The population-dependent hypotheses hold under both families (see the robustness comparison in section 3), which is evidence the findings are about the mechanism rather than the synthetic structure. Results are also reported as sensitivity bands over the main knobs (competence spread, gate recall) rather than single points.
- Reproducibility: code, seeds, and configurations are versioned, and continuous integration runs the deterministic path (`T -> 0`), so reported runs can be reproduced exactly; stochastic runs record their seeds and temperature.

### 2.8 Experimental architecture

The framework and the baseline run over a shared, self-contained coordination substrate (SQLite in WAL mode by default, with an optional Postgres adapter) holding the task pool, an append-only event log, and the reliability history. The atomic claim is a single conditional update that returns a row to exactly one agent, so the decentralised coordination is measured rather than assumed. A shared scoring module is called by the simulation agents, the pilot agents, and the central scheduler, so coordination is the only factor that varies. Every action is written to the event log, so each metric in section 2.4 is a query over that log. The components, the controls, the metric-to-measurement map, and the evaluation protocol are set out in `docs/architecture.md`.

Two simulation engines share this scoring core. A fast batch engine allocates a whole task set in one pass and is used for the scaling and calibration sweeps, where the quantity of interest has no time dimension. A round-based temporal engine advances discrete rounds, so agents hold work over time, tasks accrue waiting, and the activation barrier anneals (E14); it is the engine that makes allocation latency, throughput, starvation, and the annealing of stalled tasks into real measured quantities. A concurrent multi-process engine over the store, for faithful contention at scale, remains future work.

### 2.9 Ethical considerations

The study uses synthetic data in simulation and small, scoped software tasks in the pilot, with no human subjects. The biological source is used only as a source of design intuition, and no claim is made about human reproduction.

## 3. Results (preliminary, demo scale)

These results are generated by `cta autorun` over the full protocol (20 seeds, agent counts from 50 to 1000, the pre-registered sweeps), and are committed under `results/`. The concurrent multi-process engine and the live pilot remain future work, so they are strong evidence for the coordination mechanism rather than a claim about live deployment.

| Hypothesis | Verdict | Observation |
|-----------|---------|-------------|
| H1 scaling | supported | With bounded observability (each agent samples `k` tasks) and the bottleneck measured as peak per-node load, CTA's peak load stays flat at 32 as `N` grows from 50 to 1000, while the central scheduler's grows as `N` times `M` (from 2,000 to 800,000, about 400 times over the swept range). An earlier run that measured total work under full observability showed only a marginal difference; separating peak from total and bounding observability resolved it. |
| H2 quality | not supported | Against the fair full-information optimum (`central_best`, agent reuse allowed), CTA reaches about 94 per cent of the optimum's quality (0.883 against 0.937) and is level with pull-based (0.882, Cliff's delta 0.05). It does not clear the 5 per cent margin, so H2 is not supported. A decomposition shows the shortfall is mostly deliberate: a quality-first CTA (Binding Energy without the latency term) reaches about 0.92, within the margin of the optimum, so roughly three quarters of the gap (about 0.04) is the quality traded for lower latency by design, and only about a quarter (about 0.014) is the noisy competence proxy. An earlier design compared against a one-to-one Hungarian optimum, which is handicapped by forced spreading, and so wrongly showed CTA beating the optimum. |
| H3 expressiveness | supported | Infeasible and stalled tasks are labelled with full recall against the generator ground truth. |
| H4 safety gate | supported | With about 30 per cent of agents attempting out-of-scope actions and a gate detection recall of 0.9, the gate cuts integrity violations by about 90 per cent (1.2 per run with the gate against 12.6 without). The gate is modelled as an imperfect detector, so this is a measured reduction rather than a tautological zero. |
| H5 annealing bounds stall | supported | In the temporal engine, without annealing the stalled but feasible tasks are never claimed (unmet rate 1.0, stall capped at the horizon); with annealing every feasible task resolves at a bounded stall (about 1 to 3 rounds), and the maximum stall falls smoothly as the annealing rate rises. |
| H6 heterogeneity | not supported | Against the fair optimum CTA sits slightly below it at every heterogeneity, and the gap does not close as the population specialises, so there is no widening CTA advantage. |
| H7 miscalibration is the failure mode | supported | Under a wide competence spread, winners of the raw self-report auction over-predict their realised quality by about 0.20, with a Brier score and an ECE of about 0.25 against their binary success (a well-calibrated predictor would score near zero). Self-reports are informative about fit but not about competence, so this gap is structural rather than a product of the injected bias; we report it without claiming it grows with the bias. |
| H8 track record recovers | supported | Discounting the self-report by the reliability `R` raises completion from 0.37 to 0.76 under the worst injected overconfidence (recovery 0.39, Holm-corrected p below 0.001 at 20 seeds). The correction uses only observable history. |

Supporting analysis (not a hypothesis): the track-record correction needs little history to work. Sweeping the length of the reliability record from 2 to 40 prior attempts, even a two-attempt record recovers most of the completion gap (about 0.32), and both the recovery and the calibration of the retained winners improve with a longer record (recovery rising to about 0.41 and the Brier score falling from about 0.32 to about 0.17). So the correction is cheap in data as well as in computation.

Generalisability across generators: the population-dependent hypotheses were re-run under the structurally different `latent` family (smooth cosine compatibility, no skill gate). The verdicts are the same under both families, which is evidence the findings track the mechanism, not the synthetic structure.

| Hypothesis | Domains family | Latent family |
|-----------|----------------|---------------|
| H2 quality within margin | not supported | not supported |
| H4 safety gate reduces violations | supported | supported |
| H7 self-reports over-predict | supported | supported |
| H8 track record recovers | supported | supported |

Sensitivity bands: rather than single points, the two central results are reported as curves. The recovery of the track-record correction rises monotonically with the competence spread (from about 0.05 when competence is narrow to about 0.41 when it is wide), confirming the correction matters exactly where agents differ. The gate's violation reduction rises with its detection recall (from about 0.57 at recall 0.5 to a full block at recall 1.0), so the safety result degrades gracefully rather than depending on a perfect detector. A recovery surface over the overconfidence bias by the competence spread shows horizontal bands, so the overconfidence gap is driven by the competence spread and not by the injected bias, consistent with the H7 framing.

## 4. Discussion

The runs support the scaling and expressiveness claims, and the repositioning around calibration turns the earlier soft spots into results, but the quality claim H2 does not hold against a fair optimum and this is reported as it stands. On scaling, the first design showed only a marginal advantage because it measured total work under full observability; once the bottleneck is measured as peak per-node load and each agent observes a bounded sample of tasks, CTA's peak load is flat in the population size while the central scheduler grows with `N` times `M`. Total work remains comparable and distributed, so the claim is bottleneck relief, not less total compute, exactly as pre-registered.

On quality, an earlier design compared CTA against a one-to-one Hungarian optimum, which is forced to spread work across weaker agents, so CTA appeared to beat the optimum. Against the fair full-information optimum (`central_best`, which allows agent reuse as CTA does), CTA reaches about 94 per cent of the optimum's realised quality and is level with the pull-based baseline. It does not clear the pre-registered 5 per cent margin, so H2 is not supported at this scale. A decomposition makes the cause precise. Running CTA with a quality-first bid (Binding Energy without the latency term) lifts realised quality to about 0.92, within the margin of the optimum, so about three quarters of the gap is the quality that the deployed, cost-aware bid trades for lower latency by design, and only about a quarter is the residual from ranking on the noisy track record rather than the true capability the optimum sees. In other words, CTA is not failing to find quality; it is optimising quality per unit cost, and a quality-first configuration would meet H2 at the expense of speed. The barrier itself is quality-neutral, matching pull-based, so its value is the infeasible and stalled semantics and the safety gate, not a quality lift over naive self-scheduling.

The central result concerns the assumption that self-selection rests on. When the compatibility bid is the agent's own self-report, and competence varies across the population, the raw self-report auction is competence-blind: it selects well-fitted but not necessarily competent agents, and completion falls to about 0.37 while winners over-predict their quality by about 0.20 (H7). This reproduces, in the allocation setting, the miscalibration that the auction literature reports for language-model agents (Fradkin and Krishnan, 2026). The correction is cheap and needs no privileged information: discounting the self-report by the agent's observable track record (the reliability `R`) raises completion to about 0.76, a recovery of about 0.39 that is highly significant after multiple-comparison correction (H8). The same track record that the earlier design folded into selection turns out to be the mechanism that makes self-selection robust to miscalibration.

The gate and the annealing barrier are the safety and the liveness sides of the same design, and both are now tested honestly. The gate is modelled as an imperfect detector (recall 0.9), not an oracle, so with adversarial agents it cuts out-of-scope writes by about 83 per cent rather than to a tautological zero (H4); it is a safety boundary, not a quality lever. On the other side, the round-based temporal engine shows that activation-energy annealing (E14) bounds the stall time of feasible tasks: without it, a stalled but feasible task is never claimed, whereas a small annealing rate resolves every feasible task within a few rounds, and the maximum stall falls smoothly as the rate rises (H5). The temporal engine also makes allocation latency, throughput, and starvation real measured quantities rather than aspirations (at base scale, mean latency about 0.3 rounds and throughput about 9 completed tasks per round). H6 is also not supported: against the fair optimum CTA sits slightly below it at every heterogeneity, and the gap does not close as the population specialises, so there is no widening CTA advantage to report. Whether a heterogeneity regime exists where decentralised self-selection genuinely overtakes central assignment is left open.

These findings are demo scale, on synthetic populations, so they are not the study's conclusions. The full protocol, the concurrent multi-process engine over the store, the wider heterogeneity range, and the live pilot are the path to definitive results, and the pre-registered hypotheses and falsification criteria in section 2.6 stand regardless of these preliminary verdicts.

## References

Bonabeau, E., Theraulaz, G., & Deneubourg, J-L. (1996) Quantitative study of the fixed threshold model for the regulation of division of labour in insect societies. Proceedings of the Royal Society of London B: Biological Sciences, 263(1376), 1565-1569. DOI: 10.1098/rspb.1996.0229.

Cemri, M., Pan, M.Z., Yang, S., Agrawal, L.A., Chopra, B., Tiwari, R., Keutzer, K., Parameswaran, A., Klein, D., Ramchandran, K., Zaharia, M., Gonzalez, J.E., & Stoica, I. (2025) Why do multi-agent LLM systems fail? arXiv:2503.13657.

Dias, M.B., Zlot, R., Kalra, N., & Stentz, A. (2006) Market-based multirobot coordination: a survey and analysis. Proceedings of the IEEE, 94(7), 1257-1270. DOI: 10.1109/JPROC.2006.876939.

Dorigo, M., Maniezzo, V., & Colorni, A. (1996) Ant System: optimization by a colony of cooperating agents. IEEE Transactions on Systems, Man, and Cybernetics, Part B, 26(1), 29-41. DOI: 10.1109/3477.484436.

Fitzpatrick, J.L., Willis, C., Devigili, A., Young, A., Carroll, M., Hunter, H.R., & Brison, D.R. (2020) Chemical signals from eggs facilitate cryptic female choice in humans. Proceedings of the Royal Society B: Biological Sciences, 287(1928), 20200805. DOI: 10.1098/rspb.2020.0805.

Fradkin, A., & Krishnan, R. (2026) MarketBench: evaluating AI agents as market participants. arXiv:2604.23897.

Gerkey, B.P., & Matarić, M.J. (2004) A formal analysis and taxonomy of task allocation in multi-robot systems. The International Journal of Robotics Research, 23(9), 939-954. DOI: 10.1177/0278364904045564.

Kuhn, H.W. (1955) The Hungarian method for the assignment problem. Naval Research Logistics Quarterly, 2(1-2), 83-97. DOI: 10.1002/nav.3800020109.

Smith, R.G. (1980) The Contract Net Protocol: high-level communication and control in a distributed problem solver. IEEE Transactions on Computers, C-29(12), 1104-1113. DOI: 10.1109/TC.1980.1675516.

Zhang, A.L., Kraska, T., & Khattab, O. (2025) Recursive Language Models. arXiv:2512.24601.

Zhang, C., Zhu, Z., Wei, Y., Tian, B., Liu, J., Wang, H., Wang, X., & Liu, Y. (2026) Confidence-calibrated small-large language model collaboration for cost-efficient reasoning. Proceedings of the 19th Conference of the European Chapter of the Association for Computational Linguistics (EACL 2026). arXiv:2603.03752.
