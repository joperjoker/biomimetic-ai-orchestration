"""The bounded search space the Auto-Researcher may edit.

Only these knobs are tunable, and only within their bounds. The metrics, the
ground-truth quality, the tests, and the gate are deliberately outside this
surface, so the loop cannot tune its own success measure.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

BOUNDS: dict[str, tuple[float, float]] = {
    "activation_energy": (0.05, 0.60),
    "temperature": (0.00, 0.50),
}


@dataclass(frozen=True)
class SearchPoint:
    activation_energy: float = 0.20
    temperature: float = 0.00

    def as_dict(self) -> dict[str, float]:
        return {"activation_energy": self.activation_energy, "temperature": self.temperature}


def _clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


def propose(point: SearchPoint, rng: random.Random, step: float = 0.08) -> SearchPoint:
    """Propose a neighbour within bounds by a small seeded perturbation."""
    ea_lo, ea_hi = BOUNDS["activation_energy"]
    t_lo, t_hi = BOUNDS["temperature"]
    return SearchPoint(
        activation_energy=_clamp(
            point.activation_energy + rng.uniform(-step, step), ea_lo, ea_hi
        ),
        temperature=_clamp(point.temperature + rng.uniform(-step, step), t_lo, t_hi),
    )
