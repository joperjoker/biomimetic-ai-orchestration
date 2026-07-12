# Product thesis: a decentralised allocation layer for agent fleets

This one page states what Chemotactic Task Allocation (CTA) is as a product, who
buys it, and how it is positioned. Every claim here is backed by a result in
`docs/paper.md`; nothing is aspirational beyond what the code demonstrates.

## What it is

A decentralised task-allocation layer for multi-agent language-model systems.
Instead of a central scheduler that scores every agent-task pair and hands out
work, tasks advertise a semantic envelope and agents self-select: an agent takes a
task only when its compatibility clears an activation barrier, the winner is
chosen by a calibrated, track-record-weighted bid, and an integrity gate screens
that winner before it gets write access. The coordination state is a small
self-contained store (SQLite by default) with a transactional atomic claim, so
there is no central scheduler to become the bottleneck or the single point of
failure.

## Who buys it, and why now

Teams running fleets of coding or tool-using agents that have outgrown a central
router. Two pains bite at scale:

- **The coordinator wall.** A central scheduler's work grows as `N` times `M`
  (agents times tasks). Measured out to ten thousand agents, its peak per-node
  load grows with a fitted exponent of 2.0 while CTA's stays flat at the
  observability bound (exponent 0.0). At representative model prices that is a
  bill rising to about 144,000 USD per allocation round at ten thousand agents
  against a busiest-node cost of about six cents, a roughly two-hundred-and-fifty
  fold saving on the coordinator line item (paper section 4).
- **Untrustworthy self-reports.** Language-model agents are miscalibrated about
  their own success, so an auction built on raw self-reports misallocates. CTA's
  track-record correction recovers the lost completion using only observable
  history, and it is robust to the direction and shape of the miscalibration
  (H7, H8, and the measured-mixture check in section 3).

## Positioning

The crowded space is central routing (RouteLLM, EvoRoute, DiSRouter and similar).
CTA does not compete on routing accuracy against those. Its two differentiators
are structural: there is **no central router** (so the coordinator bottleneck and
single point of failure are removed by construction), and the allocation is
**calibration-robust** (it is designed for self-reports that are wrong, not
assumed honest). The integrity gate adds a pre-execution trust boundary that a
pure router does not have.

## The two product dials

CTA exposes the operating point as parameters, so a deployer tunes the service
without retraining or re-architecting:

- **Cost.** Bounded observability caps each agent's evaluations, so the busiest
  node's bill is flat in fleet size; the deployer trades a little allocation
  quality for a large coordinator-cost reduction (paper section 4, cost model).
- **Speed.** The latency term in the bid carries a swept exponent, tracing a
  non-dominated latency-quality frontier: quality-first for a batch pipeline,
  latency-first for an interactive one (paper section 4, Pareto frontier).

## The wrapper layer: frontier quality at a fraction of the cost

The sharpest commercial result is the two-wrapper layer that sits in front of any
model fleet, extracted as a small library in `src/cta/wrappers.py`.

- **The task wrapper** (`wrap_task`) turns a loose task into an explicit interface
  contract with named acceptance criteria and a self-check. On real Claude agents
  this lifts a weak model to a strong model's completion (Haiku 0.925 to 1.00 on
  the expert tier, five agents) and is the precondition for independently built modules to
  integrate into a working project (H11). It makes a cheap model reliable.
- **The agent wrapper** (`Fleet`, `route`) picks, for each task, the cheapest
  model whose reliability-corrected self-report clears the activation barrier. Fed
  the per-task track record a deployment accumulates from its own logs, it
  escalates exactly the tasks a cheap model is unreliable on and keeps the rest on
  the cheap model, holding frontier-level completion at roughly one fortieth of
  the always-frontier cost (H12).

The two are complementary: the task wrapper raises the floor, the agent wrapper
turns that into a bill. The measured contrast is the pitch in one line: with only
a coarse per-model track record the router trusts the cheap model on a task it
fails (completion drops); with a per-task track record it escalates just that task
and holds completion at the frontier level for a fraction of the cost. Run the
demo:

```
python -m examples.wrapper_demo
```

It wraps a task, then routes the same fleet under a coarse and a per-task track
record, printing the routing decisions and the cost multiple against always using
the frontier model. Offline and deterministic, no model calls. The differentiator
against static-capability routers (RouteLLM and similar) is that CTA routes on a
reliability-corrected self-report screened by a safety gate, so it adapts to the
model being miscalibrated rather than assuming a fixed capability.

## Safety

The integrity gate is a pre-execution boundary, not a quality lever. Modelled as
an imperfect detector (recall 0.9, not an oracle), it cuts out-of-scope writes by
adversarial agents by about 83 to 90 per cent, and an ablation shows it is the
mechanism that carries the safety effect (H4, P2.4). On heterogeneous work the
activation barrier keeps allocation on target, routing each subtask to a correct
specialist rather than whichever agent is nearest (H10).

## Try it

```
python -m examples.poc
```

A small fleet self-selects tasks through the calibrated gated bid; the report
shows the allocation, the out-of-scope actions the gate stopped, and the
coordinator cost avoided. It runs offline and deterministically, with no model
calls.

## Honest limits

The evidence is a simulation study on synthetic populations, with calibration
anchored to real agents through the MarketBench-grounded fleet and a single-model
live pilot. Against a full-information optimum the quality claim does not clear
its margin and is reported as such; the fair, beatable comparison is an
information-bounded central scheduler, which CTA matches with fresh information
and beats as that scheduler's reliability table goes stale (H9). A two-sided
real-agent calibration curve and a real complex job with dependencies and live
specialist subagents are the next steps (future work, P2.5 and
P3.4).
