"""Visualisation as pure-standard-library SVG.

Charts are written as self-contained SVG text, so no plotting library is needed
and the figures are diff-friendly and render anywhere. A matplotlib path can be
added later behind the ``viz`` extra, but it is not required. The palette is a
small, accessible, brand-neutral set that reads in light and dark.

Every chart carries a title, both axis titles, tick value labels on both axes
(with light gridlines), a legend for multi-series data, and, for bars, the value
printed on each bar, so a figure is readable on its own.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

PALETTE = ["#2f6f9f", "#c25a3d", "#4c9a6a", "#8a6fb0", "#b58b2c"]

_W, _H = 720, 440
_ML, _MR, _MT, _MB = 74, 160, 40, 64  # margins (right margin holds the legend)
_GRID = "#e8e8e8"


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _scale(v: float, lo: float, hi: float, out_lo: float, out_hi: float) -> float:
    if hi == lo:
        return (out_lo + out_hi) / 2
    return out_lo + (v - lo) / (hi - lo) * (out_hi - out_lo)


def _ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    """``n`` evenly spaced tick values across ``[lo, hi]`` (deduplicated)."""
    if hi == lo:
        return [lo]
    n = max(2, n)
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]


def line_chart(
    series: dict[str, Sequence[tuple[float, float]]],
    title: str,
    xlabel: str,
    ylabel: str,
    logx: bool = False,
    logy: bool = False,
) -> str:
    """Render a multi-series line chart to an SVG string."""
    import math

    def tx(x: float) -> float:
        return math.log10(x) if logx and x > 0 else x

    def ty(y: float) -> float:
        return math.log10(y) if logy and y > 0 else y

    xs = [tx(x) for pts in series.values() for x, _ in pts]
    ys = [ty(y) for pts in series.values() for _, y in pts]
    if not xs or not ys:
        xs, ys = [0.0, 1.0], [0.0, 1.0]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)
    if not logy:
        ylo = min(ylo, 0.0)

    px0, px1 = _ML, _W - _MR
    py0, py1 = _H - _MB, _MT
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_H}" '
        f'viewBox="0 0 {_W} {_H}" font-family="sans-serif" font-size="13">',
        f'<rect width="{_W}" height="{_H}" fill="white"/>',
        f'<text x="{_W/2:.0f}" y="22" text-anchor="middle" font-size="16">{_esc(title)}</text>',
    ]
    # Gridlines and tick value labels first, so the data draws on top.
    for t in _ticks(ylo, yhi):
        sy = _scale(t, ylo, yhi, py0, py1)
        raw = (10.0**t) if logy else t
        parts.append(f'<line x1="{px0}" y1="{sy:.1f}" x2="{px1}" y2="{sy:.1f}" stroke="{_GRID}"/>')
        parts.append(f'<text x="{px0-8}" y="{sy+4:.1f}" text-anchor="end">{_fmt(raw)}</text>')
    for t in _ticks(xlo, xhi):
        sx = _scale(t, xlo, xhi, px0, px1)
        raw = (10.0**t) if logx else t
        parts.append(f'<line x1="{sx:.1f}" y1="{py0}" x2="{sx:.1f}" y2="{py0+5}" stroke="#333"/>')
        parts.append(f'<text x="{sx:.1f}" y="{py0+18}" text-anchor="middle">{_fmt(raw)}</text>')
    # Axes and axis titles.
    parts.append(f'<line x1="{px0}" y1="{py0}" x2="{px1}" y2="{py0}" stroke="#333"/>')
    parts.append(f'<line x1="{px0}" y1="{py0}" x2="{px0}" y2="{py1}" stroke="#333"/>')
    parts.append(
        f'<text x="{(px0+px1)/2:.0f}" y="{_H-16}" text-anchor="middle">{_esc(xlabel)}</text>'
    )
    parts.append(
        f'<text x="18" y="{(py0+py1)/2:.0f}" text-anchor="middle" '
        f'transform="rotate(-90 18 {(py0+py1)/2:.0f})">{_esc(ylabel)}</text>'
    )
    for i, (label, pts) in enumerate(series.items()):
        colour = PALETTE[i % len(PALETTE)]
        coords = [
            (_scale(tx(x), xlo, xhi, px0, px1), _scale(ty(y), ylo, yhi, py0, py1))
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
    parts.append("</svg>")
    return "\n".join(parts)


def _mix(lo_hex: str, hi_hex: str, t: float) -> str:
    """Linear blend between two hex colours at fraction ``t`` in [0, 1]."""
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    a = [int(lo_hex[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(hi_hex[i : i + 2], 16) for i in (1, 3, 5)]
    c = [round(a[k] + (b[k] - a[k]) * t) for k in range(3)]
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def heatmap(
    grid: Sequence[Sequence[float]],
    row_labels: Sequence[str],
    col_labels: Sequence[str],
    title: str,
    xlabel: str,
    ylabel: str,
) -> str:
    """Render a grid of values as a colour-mapped heatmap with the values shown."""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    flat = [v for r in grid for v in r] or [0.0]
    vlo, vhi = min(flat), max(flat)
    cw, ch = 96, 54
    ml, mt = 96, 52
    w = ml + cols * cw + 40
    h = mt + rows * ch + 64
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="sans-serif" font-size="13">',
        f'<rect width="{w}" height="{h}" fill="white"/>',
        f'<text x="{w/2:.0f}" y="26" text-anchor="middle" font-size="16">{_esc(title)}</text>',
    ]
    for r in range(rows):
        for c in range(cols):
            v = grid[r][c]
            t = 0.5 if vhi == vlo else (v - vlo) / (vhi - vlo)
            x, y = ml + c * cw, mt + r * ch
            fill = _mix("#eef4f9", "#2f6f9f", t)
            txt = "#ffffff" if t > 0.55 else "#1a1a1a"
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cw-2}" height="{ch-2}" fill="{fill}"/>'
            )
            parts.append(
                f'<text x="{x+cw/2-1:.0f}" y="{y+ch/2+4:.0f}" text-anchor="middle" '
                f'fill="{txt}">{_fmt(v)}</text>'
            )
    for c in range(cols):
        parts.append(
            f'<text x="{ml+c*cw+cw/2-1:.0f}" y="{mt-8}" text-anchor="middle">'
            f'{_esc(str(col_labels[c]))}</text>'
        )
    for r in range(rows):
        parts.append(
            f'<text x="{ml-8}" y="{mt+r*ch+ch/2+4:.0f}" text-anchor="end">'
            f'{_esc(str(row_labels[r]))}</text>'
        )
    parts.append(
        f'<text x="{ml+cols*cw/2:.0f}" y="{h-16}" text-anchor="middle">{_esc(xlabel)}</text>'
    )
    parts.append(
        f'<text x="20" y="{mt+rows*ch/2:.0f}" text-anchor="middle" '
        f'transform="rotate(-90 20 {mt+rows*ch/2:.0f})">{_esc(ylabel)}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def bar_chart(
    categories: Sequence[str],
    series: dict[str, Sequence[float]],
    title: str,
    ylabel: str,
    xlabel: str = "",
) -> str:
    """Render a grouped bar chart (one group per category, one bar per series).

    Carries a y-axis scale with tick value labels and gridlines, the value printed
    on each bar, category labels, an optional x-axis title, and a legend.
    """
    vals = [v for vs in series.values() for v in vs] or [0.0]
    vhi = max(vals + [0.0])
    vlo = min(vals + [0.0])
    px0, px1 = _ML, _W - _MR
    py0, py1 = _H - _MB, _MT
    n_groups = len(categories)
    n_series = max(1, len(series))
    group_w = (px1 - px0) / max(1, n_groups)
    bar_w = group_w * 0.8 / n_series
    zero_y = _scale(0, vlo, vhi, py0, py1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_H}" '
        f'viewBox="0 0 {_W} {_H}" font-family="sans-serif" font-size="13">',
        f'<rect width="{_W}" height="{_H}" fill="white"/>',
        f'<text x="{_W/2:.0f}" y="22" text-anchor="middle" font-size="16">{_esc(title)}</text>',
    ]
    # Y-axis gridlines and tick value labels.
    for t in _ticks(vlo, vhi):
        sy = _scale(t, vlo, vhi, py0, py1)
        parts.append(f'<line x1="{px0}" y1="{sy:.1f}" x2="{px1}" y2="{sy:.1f}" stroke="{_GRID}"/>')
        parts.append(f'<text x="{px0-8}" y="{sy+4:.1f}" text-anchor="end">{_fmt(t)}</text>')
    # Zero baseline and y-axis, then axis titles.
    parts.append(f'<line x1="{px0}" y1="{zero_y:.1f}" x2="{px1}" y2="{zero_y:.1f}" stroke="#333"/>')
    parts.append(f'<line x1="{px0}" y1="{py0}" x2="{px0}" y2="{py1}" stroke="#333"/>')
    parts.append(
        f'<text x="18" y="{(py0+py1)/2:.0f}" text-anchor="middle" '
        f'transform="rotate(-90 18 {(py0+py1)/2:.0f})">{_esc(ylabel)}</text>'
    )
    if xlabel:
        parts.append(
            f'<text x="{(px0+px1)/2:.0f}" y="{_H-16}" text-anchor="middle">{_esc(xlabel)}</text>'
        )
    for gi, cat in enumerate(categories):
        gx = px0 + gi * group_w
        for si, vs in enumerate(series.values()):
            v = vs[gi] if gi < len(vs) else 0.0
            colour = PALETTE[si % len(PALETTE)]
            bx = gx + group_w * 0.1 + si * bar_w
            y1 = _scale(v, vlo, vhi, py0, py1)
            top = min(zero_y, y1)
            parts.append(
                f'<rect x="{bx:.1f}" y="{top:.1f}" width="{bar_w*0.9:.1f}" '
                f'height="{abs(y1-zero_y):.1f}" fill="{colour}"/>'
            )
            # Value printed just past the bar's end.
            vy = y1 - 4 if v >= 0 else y1 + 14
            parts.append(
                f'<text x="{bx+bar_w*0.45:.1f}" y="{vy:.1f}" text-anchor="middle" '
                f'font-size="11">{_fmt(v)}</text>'
            )
        cx = gx + group_w / 2
        parts.append(
            f'<text x="{cx:.0f}" y="{py0+18}" text-anchor="middle">{_esc(str(cat))}</text>'
        )
    for si, label in enumerate(series):
        ly = _MT + 6 + si * 22
        clr = PALETTE[si % len(PALETTE)]
        parts.append(f'<rect x="{px1+16}" y="{ly}" width="14" height="14" fill="{clr}"/>')
        parts.append(f'<text x="{px1+34}" y="{ly+12}">{_esc(label)}</text>')
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
