"""Ground-truth realised quality Q (E12).

The realised outcome of a task depends on the agent's true fit and capability,
not on the agent's self-estimate, so it can ground both the quality metric and
the compatibility calibration. Pure standard library, deterministic given the
random generator that is passed in.
"""

from __future__ import annotations

import random

Q_MIN_DEFAULT = 0.70


def _clip01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def realised_quality(
    true_compatibility: float,
    true_capability: float,
    rng: random.Random,
    sigma: float = 0.10,
) -> float:
    """Q in [0, 1], drawn from the true fit and capability plus Gaussian noise.

    The mean is the product of true compatibility and true capability, so a good
    match by a capable agent yields high quality in expectation. The noise models
    the irreducible variability of a real task outcome.
    """
    mean = _clip01(true_compatibility) * _clip01(true_capability)
    return _clip01(mean + rng.gauss(0.0, sigma))


def is_success(quality: float, q_min: float = Q_MIN_DEFAULT) -> bool:
    """An attempt succeeds when realised quality clears the threshold."""
    return quality >= q_min
