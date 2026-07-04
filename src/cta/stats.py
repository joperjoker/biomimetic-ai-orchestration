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


def bootstrap_ci(
    values: Sequence[float], boot: int = 2000, seed: int = 20240607, alpha: float = 0.05
) -> tuple[float, float, float]:
    """Mean and a percentile bootstrap confidence interval (mean, low, high).

    Resamples the values with replacement ``boot`` times and takes the empirical
    ``alpha/2`` and ``1 - alpha/2`` quantiles of the resample means. Unlike the
    normal-approximation ``mean_ci`` it makes no symmetry or normality assumption,
    which matters for the bounded, skewed quality and completion metrics. Pure
    standard library and deterministic under the seed.
    """
    import random

    n = len(values)
    if n == 0:
        return (0.0, 0.0, 0.0)
    mean = statistics.fmean(values)
    if n == 1:
        return (mean, mean, mean)
    rng = random.Random(seed)
    means = []
    for _ in range(boot):
        means.append(statistics.fmean(values[rng.randrange(n)] for _ in range(n)))
    means.sort()
    lo = means[int((alpha / 2.0) * (len(means) - 1))]
    hi = means[int((1.0 - alpha / 2.0) * (len(means) - 1))]
    return (mean, lo, hi)


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


def _ols_slope(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Ordinary-least-squares slope of ``ys`` on ``xs``. Zero variance gives 0."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0.0:
        return 0.0
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False))
    return sxy / sxx


def fit_scaling(
    ns: Sequence[float], loads: Sequence[float], boot: int = 2000, seed: int = 12345
) -> dict[str, float]:
    """Fit ``log(load) = a + b*log(N)`` and bootstrap a CI for the exponent ``b``.

    The exponent ``b`` is the growth order: about 2 for a central scheduler whose
    load is ``N`` times ``M`` (with ``M`` proportional to ``N``), and about 0 for a
    decentralised per-node load that stays flat as ``N`` grows. The CI is a
    percentile bootstrap over the points, using only the standard library. Points
    with a non-positive load or ``N`` are dropped, since the fit is in log space.
    """
    import random

    pts = [(math.log(n), math.log(v)) for n, v in zip(ns, loads, strict=False) if n > 0 and v > 0]
    if len(pts) < 2:
        return {"exponent": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n_points": len(pts)}
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    point = _ols_slope(xs, ys)
    rng = random.Random(seed)
    slopes: list[float] = []
    m = len(pts)
    for _ in range(boot):
        idx = [rng.randrange(m) for _ in range(m)]
        bx = [xs[i] for i in idx]
        by = [ys[i] for i in idx]
        slopes.append(_ols_slope(bx, by))
    slopes.sort()
    lo = slopes[int(0.025 * (len(slopes) - 1))]
    hi = slopes[int(0.975 * (len(slopes) - 1))]
    return {"exponent": point, "ci_low": lo, "ci_high": hi, "n_points": m}


def min_seeds(effect: float, sd: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Seeds per arm to detect a two-sided mean difference ``effect`` at ``power``.

    A closed-form normal approximation, ``n = 2 * ((z_alpha/2 + z_power) * sd /
    effect)^2``, rounded up. It replaces a hand-picked seed count with one tied to
    the smallest effect worth detecting. A non-positive effect returns 0 (nothing
    to power for).
    """
    if effect <= 0.0 or sd <= 0.0:
        return 0
    nd = statistics.NormalDist()
    z_alpha = nd.inv_cdf(1.0 - alpha / 2.0)
    z_power = nd.inv_cdf(power)
    n = 2.0 * ((z_alpha + z_power) * sd / effect) ** 2
    return max(2, math.ceil(n))


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
