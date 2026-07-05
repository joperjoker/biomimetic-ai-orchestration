"""The CTA wrapper layer, packaged as a small product API.

The research shows two mechanisms carry a cost result on real agents. This module
extracts them from the experiment harness into a clean, reusable interface that
sits in front of any model fleet.

- The **task wrapper** (`wrap_task`, `TaskContract`) turns a loose task into an
  explicit interface contract with named acceptance criteria and a self-check.
  On real agents this lifts a weak model to a strong model's completion and lets
  independently built modules integrate (H11).
- The **agent wrapper** (`Fleet`, `route`) picks, for each task, the cheapest
  model whose reliability-corrected self-report clears an activation barrier. Fed
  a per-task track record it escalates exactly the tasks a cheap model is
  unreliable on, holding frontier completion at a fraction of the cost (H12).

Pure standard library and deterministic. Prices come from ``cta.cost.PRICING``
(representative tiers; set your own before quoting an absolute figure).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cta.cost import PRICING

BARRIER_DEFAULT = 0.7
RELIABILITY_PRIOR = 0.6  # a fresh model with no track record on a task type


# --- The task wrapper ----------------------------------------------------------


@dataclass(frozen=True)
class TaskContract:
    """An explicit interface contract for a task: the task-wrapper output."""

    name: str
    signature: str
    description: str
    acceptance: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    self_check: tuple[str, ...] = ()

    def envelope(self) -> str:
        """Render the wrapped prompt an agent receives."""
        lines = [self.signature, f'    """{self.description}']
        if self.acceptance:
            lines.append("    Acceptance criteria (the hidden tests check these):")
            lines += [f"    - {a}" for a in self.acceptance]
        if self.examples:
            lines.append("    Examples: " + "; ".join(self.examples))
        if self.self_check:
            lines.append("    Self-check before answering: " + "; ".join(self.self_check))
        lines.append('    """')
        return "\n".join(lines)


def wrap_task(
    name: str,
    signature: str,
    description: str,
    *,
    acceptance: list[str] | None = None,
    examples: list[str] | None = None,
    self_check: list[str] | None = None,
) -> TaskContract:
    """Build a task contract (the task wrapper) from its parts."""
    return TaskContract(
        name=name,
        signature=signature,
        description=description,
        acceptance=tuple(acceptance or ()),
        examples=tuple(examples or ()),
        self_check=tuple(self_check or ()),
    )


# --- The agent wrapper ---------------------------------------------------------


@dataclass
class Model:
    """A model in the fleet, at one of the representative price tiers."""

    name: str
    tier: str  # one of cta.cost.PRICING: economy | standard | premium

    def blended_rate(self) -> float:
        """Representative USD per million tokens (mean of input and output)."""
        lo, hi = PRICING[self.tier]
        return (lo + hi) / 2.0


@dataclass
class RouteDecision:
    task: str
    model: str
    corrected_bids: dict[str, float]
    eligible: list[str]
    reason: str


@dataclass
class Fleet:
    """An ordered fleet (cheapest first) with a per-task reliability track record."""

    models: list[Model]
    barrier: float = BARRIER_DEFAULT
    # reliability[model_name][task_type] = realised pass rate from history
    reliability: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.models = sorted(self.models, key=lambda m: m.blended_rate())

    def cheapest(self) -> Model:
        return self.models[0]

    def most_capable(self) -> Model:
        return self.models[-1]

    def reliability_of(self, model: str, task_type: str) -> float:
        return self.reliability.get(model, {}).get(task_type, RELIABILITY_PRIOR)

    def record(self, model: str, task_type: str, passed: bool, weight: float = 0.3) -> None:
        """Update the track record from a realised outcome (exponential moving)."""
        cur = self.reliability.setdefault(model, {}).get(task_type, RELIABILITY_PRIOR)
        self.reliability[model][task_type] = (1 - weight) * cur + weight * (1.0 if passed else 0.0)

    def per_task_token_cost_usd(self, model: str, tokens_per_task: float) -> float:
        m = next(x for x in self.models if x.name == model)
        return (tokens_per_task / 1e6) * m.blended_rate()


def route(task_type: str, bids: dict[str, float], fleet: Fleet) -> RouteDecision:
    """Pick the cheapest model whose reliability-corrected self-report clears the
    barrier; if none clears, pick the highest corrected bid (escalate up)."""
    corrected = {
        m.name: bids.get(m.name, 0.0) * fleet.reliability_of(m.name, task_type)
        for m in fleet.models
    }
    eligible = [m.name for m in fleet.models if corrected[m.name] >= fleet.barrier]
    if eligible:
        choice = eligible[0]  # models are cheap-first, so the first eligible is cheapest
        reason = f"cheapest model clearing the barrier ({fleet.barrier:.2f})"
    else:
        choice = max(corrected, key=corrected.get)
        reason = "no model cleared the barrier; escalated to the highest corrected bid"
    return RouteDecision(task_type, choice, corrected, eligible, reason)


def cost_saving(
    routed: list[tuple[str, float]], fleet: Fleet, tokens_per_task: float = 4000.0
) -> dict[str, float]:
    """Cost of a routed plan versus always using the most capable model.

    ``routed`` is a list of (chosen_model, tokens_per_task) per task; the default
    token count applies when a task does not carry its own.
    """
    top = fleet.most_capable().name
    routed_cost = sum(fleet.per_task_token_cost_usd(m, t) for m, t in routed)
    top_cost = fleet.per_task_token_cost_usd(top, tokens_per_task) * len(routed)
    return {
        "routed_usd": routed_cost,
        "always_top_usd": top_cost,
        "saving_multiple": round(top_cost / routed_cost, 2) if routed_cost else 0.0,
    }
