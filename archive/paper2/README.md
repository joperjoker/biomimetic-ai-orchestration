# Paper 2 arXiv package

LaTeX source for Paper 2, "Calibration-Robust Routing as a Self-Improving Agent
Harness". Builds to a short preprint (currently 5 pages) with one figure, one
results table, and a bibliography. Ported from `docs/paper2.md`.

Paper 2 is the continuation of Paper 1 (`../paper1/`): Paper 1 establishes the
mechanism (a track-record correction for miscalibrated self-reports); Paper 2
deploys it as an Agent Client Protocol (ACP) broker and runs the head-to-head
against the routers a routing paper is expected to beat. Paper 1 stays frozen; work
on Paper 2 happens here.

## Contents

- `main.tex`: the paper (single-column `article` preprint style, same preamble as
  Paper 1).
- `refs.bib`: bibliography. Shares Paper 1's entries and adds the ACP specification
  (Zed Industries, 2025) and a companion-paper entry for Paper 1.
- `figures/headtohead.pdf`: the head-to-head figure, rendered from
  `../results/figures/headtohead.svg`.
- `build.sh`: local build (`pdflatex` + `bibtex` + two more `pdflatex` passes).

## Build locally

```
./build.sh          # writes main.pdf
```

## Regenerate the figure from the SVG

```
python -c "import cairosvg; cairosvg.svg2pdf(url='../results/figures/headtohead.svg', write_to='figures/headtohead.pdf')"
```

The head-to-head numbers come from `../results/headtohead/summary.json`, produced by
`python -m pilot_tasks.headtohead` (a zero-cost leave-one-replicate-out replay over
the Phase 3 ladder outcomes).

## Status

Draft. The result and figure are final; the prose is a first complete draft. Before
submitting: a final proofread, and a decision on whether to add a live end-to-end
broker vignette (the only part that would spend new agent budget; the headline
result does not need it).
