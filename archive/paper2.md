# Calibration-Robust Routing as a Self-Improving Agent Harness

**Draft for Paper 2.** Author: Teo Qing Cong Eugene (Independent). This is the
working draft; the LaTeX submission package will live in `paper2/` once the
sections settle. Paper 1 (`paper/`) establishes the mechanism (Chemotactic Task
Allocation, CTA) and the evidence that a track-record correction recovers the
completion that miscalibrated self-reports cost. Paper 2 puts that mechanism to
work: it presents CTA as a deployed router inside a real editor-agent protocol,
and runs the head-to-head comparison a routing paper is expected to carry.

## Abstract

Multi-model coding assistants must decide, on each turn, which model should answer.
The cheap-first heuristic under-serves hard turns; the always-frontier heuristic
overpays on easy ones; and routing on a model's own stated confidence fails when
that confidence is miscalibrated. We present a routing broker that corrects each
model's self-reported confidence by a persistent, per-task-type track record before
selecting the cheapest model that clears an activation barrier, and we expose it
through the Agent Client Protocol (ACP) so it runs unmodified inside real editors.
Framed as a harness in the sense of Weng (2026), the broker exhibits a
plan/route/observe/record loop over a first-class track-record store, so its routing
gets cheaper and more reliable the longer it runs. On real coding-agent outcomes
(three Claude tiers, eight expert tasks, ten replicates) evaluated by
leave-one-replicate-out cross-validation, the corrected router retains 98.8%
completion, within 0.013 of always-frontier, at 25.3 times lower cost, and beats
both naive-self-report and single-cheapest routing by 0.037 in completion. We also
report an effect that only real self-reports reveal: when a fleet's stated
confidence is uniformly high, naive-self-report routing collapses into
always-cheapest, and the track-record correction is precisely what restores the
ability to tell hard turns from easy ones.

## 1. Introduction

A deployed coding assistant with access to several models faces a per-turn
allocation problem. Sending every turn to the strongest model is reliable but
expensive; sending every turn to the cheapest is cheap but fails the turns that
need capability; and asking each model how confident it is, then routing on that,
only works if the confidence means something. Paper 1 showed, on real agents, that
model self-reports are miscalibrated (Claude's are underconfident), and that a
track-record correction, discounting each self-report by the model's realised pass
rate on that kind of task, recovers the completion the miscalibration costs.

This paper is about deployment and comparison. We make three moves.

1. **A protocol-native broker.** We present CTA as an ACP agent that routes over a
   downstream fleet: on each `session/prompt` turn it elicits a confidence bid per
   candidate, corrects it by the track record, gates it, selects the cheapest model
   that clears the activation barrier, proxies that model's reply back to the
   editor, and records the outcome. Any of roughly forty ACP-compatible editors can
   use it with no bespoke integration.
2. **A harness framing.** Following Weng (2026), the broker is a *harness*: the
   software around the base models that decides how they are chosen, what is
   remembered, and how their work is judged. Its persistent track-record store is
   what lets the deployed router self-improve across sessions rather than starting
   cold each time (the deployment form of Paper 1's H13 self-improvement result).
3. **The head-to-head.** We compare four routing policies on real agent outcomes:
   the corrected router, naive-self-report routing, always-frontier, and
   single-cheapest, reporting completion with confidence intervals, dollar cost, and
   the overhead of eliciting confidence.

## 2. Related work

**Model routing and cascades.** FrugalGPT (Chen, Zaharia, and Zou, 2023) cascades
from cheap to expensive models under a budget; RouteLLM (Ong et al., 2024) learns a
router from preference data. Both decide capability from features learned offline.
Our router instead carries an online, per-task-type reliability estimate and
corrects a *live* self-report by it, so it adapts to the fleet it is actually
running and improves in service. Confidence-calibrated small-large collaboration
(Zhang et al., 2026) is the closest in spirit; we differ in operating through a
deployment protocol and in isolating the track-record correction as the mechanism.

**Agent Client Protocol.** ACP (Zed Industries, 2025) is a JSON-RPC protocol that
lets any editor talk to any coding agent, in the spirit of LSP and MCP. It gives an
agent an editor (buffers, terminals, diffs) where MCP gives an agent tools. ACP has
no native confidence field, so eliciting one is a deliberate extension whose cost we
measure.

**Harness engineering.** Weng (2026) argues that near-term self-improvement comes
from the harness around a base model, and that such loops are only as good as the
signal they optimise: the evaluator is the weak link. A track-record correction plus
an integrity gate is a mechanism for making a self-report-based signal trustworthy,
so CTA is naturally the calibration-robust evaluation layer such a harness needs. We
build a component, not a full recursive-self-improvement system, and say so.

## 3. The broker

CTA presents as an ACP agent to the editor and acts as a client to a downstream
fleet: a routing man-in-the-middle. The transport-free core is
`AcpBroker.handle(request) -> response` (`src/cta/acp.py`); a newline-delimited-JSON
`serve()` driver hosts it for a real editor.

**The prompt-turn loop.** On each `session/prompt`:

1. **Elicit** raw confidence bids per candidate. Two modes: *prior* (a bid from a
   per-tier prior plus the track record, no extra turn) and *probe* (a short
   confidence-probe turn per candidate, a real self-report at a measured cost).
2. **Gate** the raw bids (clamp to a valid confidence range; the live form of the
   paper's integrity gate).
3. **Correct** each bid by the model's reliability on that task type, and **select**
   the cheapest model whose corrected bid clears the activation barrier, escalating
   to the highest corrected bid if none clears.
4. **Proxy** the chosen model's `session/update` stream back to the editor, tagged
   with a routing-decision update (which model, corrected confidence, why).
5. **Record** the realised outcome (hidden-test pass or user diff-accept) into the
   persistent track record, sharpening the next turn's routing.

**Harness properties.** The loop is the plan/route/observe/record cycle; the
track-record store (`store.py`, SQLite, WAL mode) is the persistent memory that
survives across sessions; the downstream fleet is the worker pool. The
differentiator over a plain router is that routing gets cheaper and more reliable the
longer the broker runs, from its own experience, with no privileged information.

## 4. Head-to-head evaluation

### 4.1 Policies

- **CTA (corrected):** cheapest model whose reliability-corrected self-report clears
  the barrier.
- **Naive self-report:** cheapest model whose *raw* self-report clears the barrier
  (no correction). Isolates what the correction buys.
- **Always frontier:** the most capable model every turn.
- **Single cheapest:** the cheapest model every turn.

### 4.2 Method: a leave-one-replicate-out replay

Routing is a decision over outcomes, so we evaluate it on outcomes already
collected without spending new budget. Paper 1's capability-ladder tier ran three
Claude tiers (Haiku, Sonnet, Opus) on eight expert coding tasks across ten
replicates, recording each run's stated confidence and hidden-test result. For each
held-out replicate we estimate every model's per-task reliability and mean
self-report from the *other* replicates, route each task under each policy, and then
look up the routed model's *actual* result on the held-out replicate. No policy sees
the outcome it is scored on. Averaging over the ten folds gives completion (with a
bootstrap confidence interval over folds), cost, and the head-to-head deltas. We use
the unaided (`bare`) condition, since the agent-router comparison should turn on the
model's own capability, not on the separate task-wrapper mechanism.

### 4.3 Results

| policy | completion (95% CI) | cost per task-set (USD) |
|--------|---------------------|-------------------------|
| CTA (corrected) | 0.988 [0.963, 1.000] | 0.057 |
| naive self-report | 0.950 [0.912, 0.988] | 0.024 |
| always frontier | 1.000 [1.000, 1.000] | 1.440 |
| single cheapest | 0.950 [0.912, 0.988] | 0.024 |

The corrected router retains 0.988 completion, within 0.013 of always-frontier, at
**25.3 times** lower cost, and beats naive-self-report and single-cheapest by
**+0.037** in completion. The gap is modest here because Haiku is already strong on
these tasks (0.950 unaided); the mechanism spends the frontier only on the roughly
one turn in twenty a cheap model actually fails, which is exactly where it should.

**An effect only real self-reports reveal.** Naive-self-report routing scores
identically to single-cheapest. Claude's stated confidence is uniformly high
(around 0.9) and always clears the barrier, so routing on the raw bid always picks
the cheapest model. Without the track-record correction, self-report routing carries
no information that distinguishes hard turns from easy ones; the correction is what
restores that information. This is a sharper statement of Paper 1's calibration
thesis, and it only appears when the self-reports are real rather than synthetic.

### 4.4 Probe overhead

Eliciting a live confidence bid costs one short probe turn per candidate; static
policies (always-frontier, single-cheapest) pay none. In the harness we account this
separately and report it as a fraction of total cost; on a three-model fleet with
short probes it stays a small fraction of the solve cost, and the track-record
correction, which needs no probe once a record exists, lets a deployment fall back to
prior mode as the record accrues.

## 5. Limitations

- **Failure-contingent advantage.** The completion gain is bounded by how often the
  cheap model actually fails. On a suite where a cheap model is already reliable, the
  correction is a cost win with no completion regression, not a completion win. We
  report the honest 0.037.
- **Underconfident fleet.** Claude self-reports are underconfident on standard
  tasks, so the overconfident failure mode that most rewards correction is not
  sourceable from this fleet without contrived tasks; we do not manufacture it. A
  fleet with a genuinely overconfident member would widen the gap.
- **Protocol youth.** ACP is recent and its remote transport is still in progress; we
  pin a spec version and stay on local stdio.
- **A component, not an RSI system.** The broker is the calibration-robust routing
  and memory layer of a harness, not a self-rewriting agent.

## 6. Conclusion

Correcting a live self-report by a persistent track record turns an unreliable
routing signal into a useful one, and doing it inside a deployment protocol makes the
resulting router usable in real editors while it improves in service. On real agent
outcomes the corrected router buys most of the frontier's reliability at a fraction of
its cost, and it is the correction, not the self-report, that does the work.

## References

Same bibliography as Paper 1 for the shared references (FrugalGPT, RouteLLM, Weng
2026, Zhang et al. 2026, MarketBench, Cemri et al. 2025), plus the ACP specification
(Zed Industries, agentclientprotocol.com). Verify every citation online before the
LaTeX build, per the project reference rule.
