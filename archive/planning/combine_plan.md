# Plan: combine Paper 1 and Paper 2 into one paper

Decision (2026-07-12): merge Paper 1 and Paper 2 into a single paper, and add a
full related-work treatment citing the close prior work. This reverses the earlier
"split" call because MARGIN (arXiv:2605.22949, May 2026) scooped Paper 2's
standalone novelty (online calibration correction of self-reports for code-agent
selection), so Paper 2's strong parts are worth more as *deployment evidence* for
Paper 1 than as a separate paper.

## Target: one paper

- **Spine:** `paper1/` (keep both editions in sync: `main.tex` plain-language,
  `main_formal.tex` technical).
- **Pull in from `paper2/main.tex` (selectively):**
  - the head-to-head result (Table + figure `headtohead.pdf`) as a Results
    subsection "corrected routing versus the alternatives",
  - the live ACP-broker vignette (Table + figure `vignette_routing.pdf`) as the
    deployment demonstration,
  - a short harness/ACP framing subsection (not a co-equal thesis).
- **Drop** Paper 2's redundant setup (it re-explains the mechanism Paper 1 already
  builds).
- **One thesis:** calibration-robust decentralised allocation; the ACP/head-to-head
  is *validation that the mechanism holds when deployed*, not a second headline.
  Current Paper 1 title still fits.
- **Retire standalone Paper 2:** move `paper2/` into `archive/` as the source it
  came from; produce a single `paper1/` build. Keep `docs/paper2.md` in archive too.

## Related work to add (verify each online before adding, per the reference rule)

Group into three, with a one-line delta each:

- **Calibration-for-selection (closest):**
  - MARGIN, arXiv:2605.22949 (online per-agent calibration for multi-agent
    coordination). Delta: MARGIN is a *centralised coordinator*; ours is
    decentralised, protocol-native (ACP), and adversarial-gaming hardened.
  - UCCI, arXiv:2605.18796 (calibrated uncertainty for cost-optimal cascade
    routing). Delta: cascade vs decentralised self-selection; no gaming model.
- **Decentralised / biomimetic:**
  - SwarmSys, arXiv:2510.10047 (pheromone-trace self-organised LLM agents). Delta:
    chemotaxis + integrity gate + coordinator-cost scaling result vs their
    pheromone/RL self-organisation.
- **Routing landscape (position, do not overclaim):** RouterDC (NeurIPS 2024),
  GraphRouter (ICLR 2025), BEST-Route (arXiv:2506.22716), and the benchmarks
  RouterBench and RouterEval. Note the honest gap: no head-to-head against these on
  a shared standard benchmark yet (still the natural next step).

Both papers already cite FrugalGPT (Chen et al. 2023) and RouteLLM (Ong et al.
2024); keep those.

## Steps (next session)

1. Add the verified citations to `paper1/refs.bib` (reuse `paper2/refs.bib`'s ACP
   and companion entries as needed; the companion self-cite is no longer needed
   once merged).
2. Copy `paper2/figures/headtohead.pdf` and `vignette_routing.pdf` into
   `paper1/figures/`.
3. In `paper1/main.tex`: add the related-work paragraphs (Section 2 or a dedicated
   Related Work section), a Results subsection for the head-to-head, and a
   deployment subsection for the ACP vignette + harness framing. Mirror all of it
   into `paper1/main_formal.tex` (formal register).
4. Reposition the contribution list to include the deployment + head-to-head, and
   soften any claim that the track-record correction itself is novel (cite MARGIN).
5. `git mv paper2 archive/paper2`; `git mv docs/paper2.md archive/`.
6. Rebuild both editions (`paper1/build.sh`), run `pytest` + `ruff` + the
   forbidden-dash check, confirm no undefined citations and no overfull boxes.
7. Update README layout (one paper now), commit, push.

## Guardrails

- British English; no clause-separating dash in `.md`; keep numbers exact and
  unchanged; keep the accessible-but-credible voice in `main.tex` and the formal
  register in `main_formal.tex`.
- Verify every new citation online before adding it.
- Watch length: target roughly 16-20 pages; if the ACP material reads as a second
  thesis rather than validation, that is the signal to reconsider the merge.
