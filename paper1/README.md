# arXiv submission package

LaTeX source for the paper, converted from `docs/paper.md`. Builds to a 17-page
preprint with vector figures, several tables, and a bibliography.

## Two editions

The paper ships in two editions that share identical results, figures, tables, and
bibliography; only the prose register and the title differ. Pick whichever suits
the audience; submit one.

- `main.tex` (plain-language edition): "From Self-Reports to Track Records:
  Calibration-Robust Task Allocation for Decentralised Multi-Agent LLM Systems".
  Short sentences, active voice, every term defined in plain words on first use.
  The title leads with the paper's core move: replacing an unreliable signal
  (self-assessment) with an observable one (the track record).
- `main_formal.tex` (technical edition): "Calibration-Robust Decentralised Task
  Allocation for Multi-Agent LLM Systems". The denser, conventional register.

Each carries a one-line note under its title pointing to the other. Keep the two in
sync when results change: edit both, or edit one and re-diff.

## Contents

- `main.tex`: the plain-language edition (single-column `article` preprint style).
- `main_formal.tex`: the technical edition (same content, formal register).
- `refs.bib`: bibliography (BibTeX).
- `main.bbl`: the compiled bibliography; include it in the arXiv upload so the
  references render even if arXiv's BibTeX pass differs.
- `figures/*.pdf`: the seven figures as vector PDFs (rendered from the committed
  SVGs in `results/figures/` via cairosvg; regenerate with the snippet below).
- `build.sh`: local build (`pdflatex` + `bibtex` + two more `pdflatex` passes).

## Build locally

```
./build.sh          # writes main.pdf
```

Requires a TeX distribution with `pdflatex`, `bibtex`, and the standard packages
(`geometry`, `graphicx`, `booktabs`, `amsmath`, `natbib`, `hyperref`, `mathptmx`).

## Regenerate the figure PDFs from the SVGs

```
python - <<'PY'
import cairosvg
figs = ["cost_vs_n","exposure_cap","ladder_completion","ladder_cost_fidelity",
        "project_modules","sandbagging_adversary","track_record_recovery"]
for f in figs:
    cairosvg.svg2pdf(url=f"../results/figures/{f}.svg", write_to=f"figures/{f}.pdf")
PY
```

## Submitting to arXiv

Upload a single archive containing `main.tex`, `refs.bib`, `main.bbl`, and the
`figures/` directory (arXiv compiles the source server-side; the included `.bbl`
guarantees the references). Primary category suggestion: **cs.MA** (Multiagent
Systems), cross-list **cs.DC** and **cs.LG**.

## Before submitting

- The author block in `main.tex` is filled in (Teo Qing Cong Eugene, Independent).
- The two forward-dated references are confirmed: MarketBench (Fradkin and
  Krishnan, arXiv:2604.23897) and Zhang et al. (EACL 2026, arXiv:2603.03752).
  Re-confirm their final venues at submission time if newer versions appear.
