"""Visualisation as pure-standard-library SVG.

Charts are written as self-contained SVG text, so no plotting library is needed
and the figures are diff-friendly and render anywhere. A matplotlib path can be
added later behind the ``viz`` extra, but it is not required. The palette is a
small, accessible, brand-neutral set that reads in light and dark.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

PALETTE = ["#2f6f9f", "#c25a3d", "#4c9a6a", "#8a6fb0", "#b58b2c"]

_W, _H = 720, 440
_ML, _MR, _MT, _MB = 70, 160, 40, 60  # margins (right margin holds the legend)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _scale(v: float, lo: float, hi: float, out_lo: float, out_hi: float) -> float:
    if hi == lo:
        return (out_lo + out_hi) / 2
    return out_lo + (v - lo) / (hi - lo) * (out_hi - out_lo)


def line_chart(
    series: dict[str, Sequence[tuple[float, float]]],
    title: str,
    xlabel: str,
    ylabel: str,
    logx: bool = False,
) -> str:
    """Render a multi-series line chart to an SVG string."""
    import math

    def tx(x: float) -> float:
        return math.log10(x) if logx and x > 0 else x

    xs = [tx(x) for pts in series.values() for x, _ in pts]
    ys = [y for pts in series.values() for _, y in pts]
    if not xs or not ys:
        xs, ys = [0.0, 1.0], [0.0, 1.0]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)
    ylo = min(ylo, 0.0)

    px0, px1 = _ML, _W - _MR
    py0, py1 = _H - _MB, _MT
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_H}" '
        f'viewBox="0 0 {_W} {_H}" font-family="sans-serif" font-size="13">',
        f'<rect width="{_W}" height="{_H}" fill="white"/>',
        f'<text x="{_W/2:.0f}" y="22" text-anchor="middle" font-size="16">{_esc(title)}</text>',
        f'<line x1="{px0}" y1="{py0}" x2="{px1}" y2="{py0}" stroke="#333"/>',
        f'<line x1="{px0}" y1="{py0}" x2="{px0}" y2="{py1}" stroke="#333"/>',
        f'<text x="{(px0+px1)/2:.0f}" y="{_H-18}" text-anchor="middle">{_esc(xlabel)}</text>',
        f'<text x="18" y="{(py0+py1)/2:.0f}" text-anchor="middle" '
        f'transform="rotate(-90 18 {(py0+py1)/2:.0f})">{_esc(ylabel)}</text>',
    ]
    for i, (label, pts) in enumerate(series.items()):
        colour = PALETTE[i % len(PALETTE)]
        coords = [
            (
                _scale(tx(x), xlo, xhi, px0, px1),
                _scale(y, ylo, yhi, py0, py1),
            )
            for x, y in pts
        ]
        path = " ".join(
            f"{'M' if k == 0 else 'L'}{x:.1f} {y:.1f}" for k, (x, y) in enumerate(coords)
        )
        parts.append(f'<path d="{path}" fill="none" stroke="{colour}" stroke-width="2.5"/>')
        for x, y in coords:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{colour}"/>')
        ly = _MT + 6 + i * 22
        parts.append(f'<rect x="{px1+16}" y="{ly}" width="14" height="14" fill="{colour}"/>')
        parts.append(f'<text x="{px1+34}" y="{ly+12}">{_esc(label)}</text>')
    # Axis end labels.
    raw_x = [x for x, _ in _flat(series)]
    x_min_lbl, x_max_lbl = _fmt(min(raw_x)), _fmt(max(raw_x))
    parts.append(f'<text x="{px0}" y="{py0+18}" text-anchor="middle">{x_min_lbl}</text>')
    parts.append(f'<text x="{px1}" y="{py0+18}" text-anchor="middle">{x_max_lbl}</text>')
    parts.append(f'<text x="{px0-8}" y="{py0}" text-anchor="end">{_fmt(ylo)}</text>')
    parts.append(f'<text x="{px0-8}" y="{py1+10}" text-anchor="end">{_fmt(yhi)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _flat(series: dict[str, Sequence[tuple[float, float]]]) -> list[tuple[float, float]]:
    return [pt for pts in series.values() for pt in pts] or [(0.0, 0.0)]


def _fmt(v: float) -> str:
    if abs(v) >= 1000 or (v != 0 and abs(v) < 0.01):
        return f"{v:.2g}"
    return f"{v:.2f}" if v != int(v) else str(int(v))


def save_svg(svg: str, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(svg, encoding="utf-8")
