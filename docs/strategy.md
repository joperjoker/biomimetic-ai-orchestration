# Strategy: from a broad research artifact to a robust paper and a product

This document records the decision on how to take the project forward. It exists
because a robust research paper and a shippable product are two different
artifacts, and the repository has so far tried to be both at once. The way
forward is to sharpen to one thesis, harden the evidence behind it, and separate
the product from the paper so each is clean.

## The core asset

Stripped of breadth, the defensible and commercially valuable finding is one
sentence:

> Route each task by calibrated confidence and track record, wrap tasks in
> interface contracts, and a cheap-model fleet matches frontier-model quality at
> roughly one fortieth of the cost.

That is the spine. The calibration-robustness mechanism (self-report
miscalibration is the failure mode of self-selection; a track-record correction
recovers it), the integrity gate, and the synthetic scaling results are support
for that claim, not co-headliners. Framing them as equals dilutes both the paper
and the pitch.

The moat is the calibration insight. Existing routers (RouteLLM, EvoRoute,
DiSRouter) route on static capability. This routes on reliability-corrected
self-report screened by a safety gate, which is the non-obvious part.

## The recommended path

### 1. Pick the thesis and elevate the wrapper results to hypotheses

Decision: elevate the two wrapper findings from external-validity contributions to
first-class, pre-registered-going-forward hypotheses.

- **H11 (task-wrapper lift):** wrapping a task in an explicit interface contract
  and acceptance criteria raises weak-model completion toward the frontier and
  is a precondition for independently built modules to integrate. Evidence:
  ladder (Haiku 0.875 to 1.00) and project (every model 0 to 1.00 completion).
- **H12 (agent-wrapper cost-efficiency):** routing by reliability-corrected
  self-report holds frontier-level completion at a fraction of the
  always-frontier cost when tasks are wrapped, and loses completion when they are
  not. Evidence: ladder (~47x) and project assembly (~39x).

The calibration-robustness mechanism (H7, H8) becomes the explanation for why
H12 works. Stating H11 and H12 as claims with an explicit success criterion turns
the strongest results from "we noticed" into "we claim and show".

### 2. Harden the evidence (the real robustness gap)

The wrapper results are currently thin for a robust paper. Close these before
submission, because a reviewer or a customer will press on exactly these points.

- **Statistical power.** One to two agents per cell today. Raise to five to eight
  per model and condition and report bootstrap confidence intervals, matching the
  bar the synthetic side already meets.
- **Routing discrimination.** Routing currently sends every task to the cheapest
  model, so it does not visibly discriminate. Construct a task mix whose optimal
  route is genuinely split (some tasks to the frontier model, some to the small
  one) so the router is shown choosing, which is the product's core value.
- **Generality.** One expert tier and one project are not enough. Add a second
  project and a broader task family to show the lift is not a single-domain
  artefact.
- **Ground the cost multiple.** Replace representative price tiers with a dated
  price snapshot and a sensitivity band, so the headline multiple survives
  scrutiny.
- **The open two-sided calibration gap.** There is still no real overconfident
  data (both Claude families are underconfident in distribution). Populate the
  overconfident arm of the reliability curve with an out-of-distribution task
  tier or a genuinely overconfident model family, or state it as a scoped
  limitation.

### 3. Separate the artifacts

Stop making one repository serve both goals.

- **Paper:** a LaTeX or PDF build with one tight thesis, a related-work table
  versus RouteLLM, EvoRoute, DiSRouter and MarketBench, print-safe figures, and
  the hardened evidence above.
- **Product:** extract the wrapper layer into a small, runnable library with a
  clean API (`wrap_task(spec) -> contract envelope` and
  `route(task, fleet) -> model`), a demo, a benchmark harness, and the cost
  dashboard. `docs/product.md` becomes real code under `examples/`.

## Commercial framing (for the product)

- **Value proposition:** frontier quality at a fraction of the cost, delivered by
  a routing and contract layer that sits in front of any model fleet.
- **Defensibility:** the calibration insight. Competitors route on capability;
  this routes on reliability-corrected self-report with a safety gate.
- **Buyer:** teams running agent or coding fleets who need cost control without a
  quality regression. The pitch is finance-legible: the same output at a fraction
  of the bill.
- **Wedge:** the task wrapper is the quietly valuable half. It makes cheap models
  reliable and makes multi-agent output composable. The project result shows that
  without the interface contract even the frontier model could not ship a working
  multi-module project.

## Next moves, in order

1. **Coherence pass on `docs/paper.md`** (cheap, about one session): restructure
   section 3 into one arc with a unified results table, re-centre the abstract and
   contributions on the wrapper-and-cost thesis, and lock the H11 and H12 framing.
   Refresh `cta dashboard` to inline the ladder and project figures.
2. **One evidence-hardening sprint** (needs subagent budget): more agents per
   cell, a split-routing scenario, and a second project, so the numbers gain
   confidence intervals and the router visibly discriminates.
3. **Extract the product** (cheap): the wrapper layer as a runnable library plus a
   demo and the cost dashboard.
4. **Publication track** (non-code): venue choice, the LaTeX or PDF conversion,
   the related-work table, and abstract polish.

## Decisions locked here

- The paper's thesis is calibration-robust, cost-optimal orchestration, with the
  task wrapper and agent wrapper as the empirical climax and the
  calibration-robustness mechanism as the explanation.
- The wrapper results are elevated to hypotheses H11 and H12.
- The product is the wrapper layer, extracted as a separate runnable artifact.
