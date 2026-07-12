# Publication strategy: unified vs split, and the next step

Decision doc for where this research goes next. Written after Phase 3 completed
(the real-agent ladder is powered to about ten agents per cell and the project to
five, each with bootstrap confidence intervals), so the real-agent claims are no
longer a "small sample".

## Where the work stands

- **Synthetic core (at scale):** eleven pre-registered hypotheses (H1-H10, H13),
  nine supported and two honest negatives (H2, H6 quality against a
  full-information optimum). Calibration-robust self-allocation is the thesis;
  flat-vs-quadratic coordination scaling to 10k agents; adversary robustness
  (strategic, sandbagging, exposure cap); H13 self-improving allocation.
- **Real-agent wrappers (powered):** task-wrapper lift (Haiku 0.950 -> 0.986, CIs
  on every ladder cell), agent-wrapper routing at ~47x cost saving, the
  dependency-graph project (bare fails, wrapped delivers, for every model across
  five replicates). Harness-engineering positioning (Weng 2026) and an ACP
  integration plan.
- **Reproducible** from seeds by one command; deterministic; British English;
  honestly scoped throughout.

## Is it ready? Calibrated venue map

- **Ready now:** TMLR (correctness/rigor/reproducibility, no novelty bar) or a
  strong agents/efficiency workshop.
- **Not yet:** top-tier main track (NeurIPS/ICML/ICLR). The one structural gap
  Phase 3 did not close: no head-to-head against a named SOTA router (RouteLLM,
  EvoRoute, DiSRouter) on an established benchmark (SWE-bench and similar); the
  task sets are bespoke.

## The two contributions (why a split is even on the table)

- **A -- the mechanism:** calibration-robust self-allocation, scaling, adversary
  robustness, H13. A rigorous simulation/theory paper.
- **B -- the wrappers:** interface contracts + calibrated routing, "cheap agents
  match frontier at ~1/47th cost", harness/ACP. An empirical/systems paper.

## Path 1: unified paper -> TMLR / strong workshop (near-term, low risk)

Keep the arc intact (mechanism -> confirmed on real agents -> cost product, tied
by the calibration thread). Steps:

1. Polish pass (free): tighten the narrative, verify every number against
   `results/`, finish related work (harness engineering, LLM routers, MarketBench).
2. Held-out second expert suite (small metered run): a new 8-task tier at
   Haiku/Sonnet n=3 to show the wrapper lift is not overfit to one suite (~6-10
   subagent runs).
3. Live price quote (free): replace representative tiers with a current quote for
   the headline cost multiples, or keep representative and label sharply.
4. Final `cta reproduce-all`, `/verify`, build `docs/paper.pdf`.
5. Submit to TMLR.

Effort: low. Metered usage: minimal (the optional held-out suite). Risk: low.

## Path 2: split, aim top-tier (higher payoff, more work)

- **Paper A (mechanism)** -> AAMAS / TMLR: essentially the synthetic core as-is,
  developed with more room for the scaling and adversary analysis.
- **Paper B (wrappers/systems)** -> top LLM/agents venue, but only after the
  differentiator lands:
  1. Build the ACP broker (P4.1-P4.5 in `docs/acp_integration.md`; mostly free
     plumbing, stdlib JSON-RPC).
  2. **The SOTA head-to-head (the differentiator, metered):** CTA's calibrated
     router vs a named router vs single-frontier, on an established benchmark
     (e.g. a SWE-bench-Lite / HumanEval+ / MBPP+ subset), run live through the
     broker. Report completion, cost, and the confidence-elicitation overhead.
  3. Fold the harness/ACP framing in as the systems contribution.

Effort: high. Metered usage: significant (benchmark runs across models). Risk:
higher, top-tier payoff.

## Recommendation (lowest-regret ordering)

The SOTA head-to-head helps **either** path, so sequence to keep both open:

1. **Now:** do the Path 1 polish and get the unified paper submission-ready for
   TMLR. This is the floor -- a solid publication in hand.
2. **Next:** pursue the SOTA-benchmark head-to-head (built on the ACP broker).
3. **Then decide:** if the head-to-head lands well, either **upgrade the unified
   paper in place** (strengthening it toward a better venue) or **split B out**
   and aim it top-tier, keeping A for a multi-agent venue.

This way the near-term publication never waits on the ambitious work, and the
ambitious work is useful whichever way the split decision goes.

## Shared next steps regardless of path

- Held-out second expert suite (generalization).
- Live price quote for the cost multiples.
- ACP broker build (also the product surface and the head-to-head vehicle).
- Optional: the harder-tier OOD retry for the two-sided calibration arm, treated
  cautiously to avoid the gotcha critique (current honest finding: Claude is
  underconfident even out-of-distribution).
