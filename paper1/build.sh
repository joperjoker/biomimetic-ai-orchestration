#!/usr/bin/env bash
# Build both editions of the paper. Requires a LaTeX toolchain (pdflatex + bibtex).
#   main.tex        -> main.pdf         (plain-language edition)
#   main_formal.tex -> main_formal.pdf  (technical edition)
# Both share the same results, figures, and refs.bib; only the prose register and
# the title differ. Pass an argument (main or main_formal) to build just one.
set -e
cd "$(dirname "$0")"

build_one() {
  local stem="$1"
  pdflatex -interaction=nonstopmode -halt-on-error "$stem.tex"
  bibtex "$stem"
  pdflatex -interaction=nonstopmode -halt-on-error "$stem.tex"
  pdflatex -interaction=nonstopmode -halt-on-error "$stem.tex"
  echo "wrote $stem.pdf"
}

if [ -n "$1" ]; then
  build_one "$1"
else
  build_one main
  build_one main_formal
fi
