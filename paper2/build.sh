#!/usr/bin/env bash
# Build the Paper 2 PDF. Requires a LaTeX toolchain (pdflatex + bibtex).
set -e
cd "$(dirname "$0")"
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
echo "wrote main.pdf"
