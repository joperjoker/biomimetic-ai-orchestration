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
specialist subagents are the next steps (`docs/next_experiments.md`, P2.5 and
P3.4).
