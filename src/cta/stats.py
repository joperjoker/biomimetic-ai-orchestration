"""Statistics for the analysis, pure standard library.

Confidence intervals, the Mann-Whitney U test (normal approximation with tie
correction, using ``statistics.NormalDist`` for the normal CDF), Cliff's delta
as a non-parametric effect size, and Holm-Bonferroni correction for the family
of secondary hypotheses. No numpy or scipy required.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

Z_95 = 1.959963984540054


def mean_ci(values: Sequence[float], z: float = Z_95) -> tuple[float, float, float]:
    """Mean and a normal-approximation confidence interval (mean, low, high)."""
    n = len(values)
    if n == 0:
        return (0.0, 0.0, 0.0)
    mean = statistics.fmean(values)
    if n == 1:
        return (mean, mean, mean)
    sd = statistics.stdev(values)
    half = z * sd / math.sqrt(n)
    return (mean, mean - half, mean + half)


def _average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1  # ranks are 1-based
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def mann_whitney_u(x: Sequence[float], y: Sequence[float]) -> tuple[float, float]:
    """Return (U, two-sided p-value) via the normal approximation with tie correction."""
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return (0.0, 1.0)
    combined = list(x) + list(y)
    ranks = _average_ranks(combined)
    r1 = sum(ranks[:n1])
    u1 = r1 - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    u = min(u1, u2)
    mu = n1 * n2 / 2
    # Tie correction for the variance.
    counts: dict[float, int] = {}
    for v in combined:
        counts[v] = counts.get(v, 0) + 1
    n = n1 + n2
    tie_term = sum(t**3 - t for t in counts.values())
    var = n1 * n2 / 12 * ((n + 1) - tie_term / (n * (n - 1))) if n > 1 else 0.0
    if var <= 0.0:
        return (u, 1.0)
    z = (u - mu) / math.sqrt(var)
    p = 2 * statistics.NormalDist().cdf(-abs(z))
    return (u, min(1.0, p))


def cliffs_delta(x: Sequence[float], y: Sequence[float]) -> float:
    """Cliff's delta effect size in [-1, 1]: P(x > y) - P(x < y)."""
    if not x or not y:
        return 0.0
    gt = lt = 0
    for a in x:
        for b in y:
            if a > b:
                gt += 1
            elif a < b:
                lt += 1
    return (gt - lt) / (len(x) * len(y))


def holm_bonferroni(pvalues: Sequence[float], alpha: float = 0.05) -> list[tuple[float, bool]]:
    """Holm-Bonferroni step-down. Returns (adjusted_p, rejected) in input order."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        adj = min(1.0, (m - rank) * pvalues[idx])
        running = max(running, adj)  # enforce monotonicity
        adjusted[idx] = running
    return [(adjusted[i], adjusted[i] <= alpha) for i in range(m)]
