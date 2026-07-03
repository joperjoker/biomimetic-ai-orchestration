# Measurable Model: Operational Definitions

This document makes every quantity in Chemotactic Task Allocation (CTA) concrete and measurable, so the research is clear, reproducible, and useful. It is the operational companion to the formal framework in `docs/paper.md` section 2.2. The guiding rule: no quantity is left as an abstract score; each is defined as a function of measured inputs, with the data source named.

## 1. Entities as concrete records

Agent `a`:
- `role`: a short text label (for example "test author", "refactorer").
- `skills`: a set of skill tags (for example {python, pytest, typing}).
- `prompt`: the system prompt text.
- `tools`: the set of tools the agent can call.
- `model`: the model identifier (fixes capability and throughput priors).
- `scope`: the set of path globs the agent is permitted to modify.
- `history`: past records `(domain, success, Q)` for reliability.

Task `t`:
- `description`: the requirement text.
- `required_skills`, `required_tools`: sets.
- `scope`: the set of path globs the task may touch.
- `domain`: a category tag.
- `complexity`: a measured index (section 7).
- `Ea`: the activation barrier (section 8).
- `priority`.

## 2. Eligibility (hard binary gate)

Eligibility screens the must-haves before any graded score:

```
elig(a, t) = 1  if  required_tools(t) subset tools(a)  and  scope(t) subset scope(a)
           = 0  otherwise
```

Tools and permitted scope are hard requirements (a safety and capability floor). Skills are graded into compatibility rather than vetoed, so a partially skilled agent can still compete at a lower score. No eligible agent means the task is infeasible.

## 3. The Task Wrapper and the compatibility score `c`

The wrapper is the mechanism that reads an agent's role, skills, and prompt against the task requirements and returns a compatibility score `c(a, t)` in [0, 1]. It replaces the abstract signal `S` with measured sub-scores.

Sub-scores (each in [0, 1]):

- Semantic match: `s_sem = clip(cos(embed(role ++ skills ++ prompt), embed(description)), 0, 1)`. The embedding model is pinned (for example a fixed sentence-transformer), so the score is deterministic. In simulation the embeddings are seeded synthetic vectors with a controllable alignment to the task; in the live pilot they are real embeddings of the agent descriptor and the task text.
- Skill coverage: `s_skill = |required_skills(t) intersect skills(a)| / |required_skills(t)|`, and 1 when the task lists no required skills.
- Scope and role fit: `s_scope = fraction of task scope globs covered by the agent's permitted scope`, computed by glob matching.

Aggregation (the wrapper's output). Four options were explored:

- Arithmetic mean `c = sum_i w_i s_i` (interpretable, but a zero in one dimension does not veto).
- Geometric mean `c = product_i (s_i + eps)^{w_i}` (a near-zero in any dimension craters `c`, scale-free in [0, 1]).
- Soft minimum (a bottleneck reading, the weakest link dominates).
- Calibrated logistic `c = 1 / (1 + exp(-(beta_0 + sum_i beta_i s_i)))`, with the coefficients fit to predict realised success.

Decision (most measurable and useful): the geometric mean is the default, with documented weights `w_sem = 0.50, w_skill = 0.35, w_scope = 0.15` (revisable), so the wrapper runs with no calibration data. When a calibration set of labelled outcomes exists, fit the logistic form to predict success (`Q >= q_min`) and use it, because it turns `c` into an empirically validated predictor rather than an assumed formula.

Predictive validity (a reportable result): measure how well `c` predicts success with the area under the ROC curve and a calibration curve (Brier score). A compatibility score that does not predict success is not useful, so this is a first-class check, not an afterthought. Target: AUC above 0.7 for `c` to be considered meaningful.

## 4. Capability `C` and effective capability

Capability is a separate agent attribute, not part of the role and prompt match, so it does not double-count with `c`:

```
C(a, t) = the agent's measured pass rate on a held-out calibration set for domain(t), in [0, 1]
```

Before any history, `C` uses the model's published prior for the task category. Effective capability couples reliability in: `C_tilde = C x R` (section 5).

## 5. Reliability `R`

```
R(a) = (s + 1) / (n + 2)
```

over a sliding window of the agent's recent attempts, where `s` is successes and `n` is total attempts. A domain-conditioned variant `R_domain` uses only attempts in `domain(t)` and is preferred when enough history exists.

## 6. Cost and latency `L`

- A priori estimate (used for selection): `L_est(a, t) = clip( estimated_tokens(t) / throughput_prior(model(a)) / L_typical, eps, L_cap )`, normalised so a typical task and model give roughly 1.
- Realised (used for reporting): the measured tokens and wall-clock time of the attempt.

Both are objective: tokens and wall-clock are measured directly, and the estimate is a function of task size and a per-model throughput prior.

## 7. Task complexity `comp(t)`

An objective index in [0, 1] from code-level proxies, min-max normalised across the task set:

```
comp(t) = weighted mean of normalised { number of files in scope, lines to change,
          number of required skills, number of tests, mean cyclomatic complexity of touched code }
```

All proxies are measured from the repository or the reference patch.

## 8. Activation energy `Ea(t)`

The barrier is measured from task attributes rather than fixed by hand:

```
Ea(t) = clip( Ea_base + w_risk x risk(t) + w_comp x comp(t), 0, 1 )
```

with defaults `Ea_base = 0.20, w_risk = 0.30, w_comp = 0.20` (revisable). `risk(t)` is measurable: 1 when the task scope touches protected globs (for example continuous integration, security, or database migrations), otherwise the fraction of high-blast-radius files in scope. Demanding or risky tasks therefore raise the compatibility an agent must reach.

## 9. Ground-truth quality `Q`

For coding tasks the outcome is objective:

```
Q(a, t) = 0.70 x (required tests passed / required tests total)
        + 0.15 x lint_pass
        + 0.10 x typecheck_pass
        + 0.05 x scope_respected
```

each term in [0, 1]. Success is `Q >= q_min`, with the default that all required tests pass and the change stays in scope. `Q` is independent of the agent's self-estimate, so it grounds the quality metric and the compatibility calibration.

## 10. Selection score (Binding Energy) `B`

Activation gates on compatibility alone (`c >= Ea`). Among the agents that fire, the winner maximises the cost-adjusted, reliability-weighted compatibility:

```
B(a, t) = c(a, t) x C_tilde(a, t) / max(L_est(a, t), eps)
```

Compatibility decides whether an agent may take a task; `B` decides which of the willing agents wins. The tie breaker is the lower `L_est`, then the lower agent identifier.

## 11. Self-reported compatibility, integrity, and the calibration metrics

The agent does not observe its true compatibility. It reports a self-assessed value (E13):

```
c_hat(a, t) = clip01(c(a, t) + bias(a) + noise(a) x N(0, 1))
```

where `bias(a)` is the agent's overconfidence (positive over-predicts) and `noise(a)` its random error. In the stress regime the bias is concentrated in less capable agents, `bias(a) = beta x (1 - C(a))`, the documented pattern where weaker performers overestimate themselves. Firing (`c_hat >= Ea`) and the bid use `c_hat`; realised quality `Q` uses the true `c`, so miscalibration corrupts the allocation without touching the ground truth.

The bid may use only signals available at allocation time. Three modes are compared:

- `raw`: the self-report alone, `c_hat / L`, the naive auction.
- `reliability`: the self-report discounted by the observable track record, `c_hat x R / L`, the correction.
- `true`: the full-information reference, `c x C / L`, the oracle that knows the true fit and competence.

Integrity is a per-execution draw: the winner acts out of scope with probability `out_of_scope_prob(a)`. The Rejection Gate (E11) is an imperfect detector: it catches an out-of-scope action with recall `scope_recall < 1` and deflects it as a prevented violation, and misses it otherwise so the action executes and is counted as an integrity violation. Without the gate every out-of-scope action executes. The safety result is therefore the measured reduction in violations, not a tautological zero.

The temporal engine adds the time-based quantities. A task open for `w` rounds has an annealed barrier `Ea_eff = max(Ea_min, Ea - anneal_rate x w)` (E14). Allocation latency is the rounds from advertisement to a successful claim, the stall time is the rounds a task waits before it is claimed, starvation is the maximum stall over feasible tasks, and throughput is completed tasks per round. An infeasible task (no eligible agent) is resolved at once and never annealed, so annealing bounds the stall of feasible tasks only.

Derived measures for the calibration study, each a query over the event log:

| Measure | Definition |
|---------|------------|
| completion rate | completed tasks / total tasks |
| overconfidence gap | mean winner `c_hat` minus mean winner realised `Q` |
| Brier score | mean squared error of winner `c_hat` against binary success |
| ECE | binned expected calibration error of winner `c_hat` against success |
| reliability diagram | per-bin mean prediction versus realised success; the diagonal is perfect calibration, below it is overconfident |
| recovery | completion under `reliability` minus completion under `raw` |
| track-record length | prior attempts behind `R`; swept to show the history the correction needs |
| integrity violations | out-of-scope actions that executed (gate off) |

## 12. What is measured versus assumed

| Quantity | Measured from | Assumed or configured |
|----------|---------------|-----------------------|
| `s_sem` | embedding cosine (pinned model) | the embedding model choice |
| `s_skill`, `s_scope` | set and glob operations | nothing |
| `c` weights or logistic coefficients | fit to labelled success | default weights before calibration |
| `C` | calibration-set pass rate | the model prior before history |
| `R` | attempt history | window size |
| `L_est` | task size and throughput prior | normalisation constants |
| `comp`, `risk` | repository and scope | proxy weights, protected globs |
| `Ea` | `comp` and `risk` | `Ea_base` and its weights |
| `Q` | tests, lint, types, scope | the term weights and `q_min` |

## 13. Calibration procedure

1. Generate a labelled set of `(agent, task, sub-scores, realised Q, success)` from simulation and a small live batch.
2. Fit the logistic compatibility model and the `Q` term weights.
3. Report predictive validity (AUC, Brier score) and freeze the fitted parameters with a config hash.
4. Re-fit only through the human-gated calibration step, never inside the autonomous loop, so the loop cannot tune its own success metric.
