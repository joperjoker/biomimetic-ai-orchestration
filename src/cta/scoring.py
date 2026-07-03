"""The CTA scoring model: operational definitions E1 to E11.

Pure functions and small dataclasses with no external dependencies, so the core
is fast, deterministic, and easy to test. The equation labels (E1 to E11) match
`docs/paper.md` section 2.2, and every quantity is defined in `docs/measures.md`.

Conventions:
- Compatibility ``c`` in [0, 1] is produced by the task wrapper from an agent's
  role, skills, and prompt against the task requirements. It replaces the older
  abstract signal ``S``.
- The activation barrier is compared against compatibility (``c >= Ea``).
- Binding Energy ``B = c * C_tilde / L`` ranks the agents that have cleared the
  barrier; it does not gate firing.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

EPS = 0.01
"""Latency floor, so Binding Energy stays bounded (E6)."""

COMPAT_FLOOR = 1e-3
"""Floor for a compatibility sub-score, so a zero is a strong (but finite) penalty
in the geometric mean without pushing a perfect score above its true value."""


@dataclass(frozen=True)
class Task:
    """A unit of work and its wrapper metadata (the scent envelope).

    ``requirement_vector`` is a normalised embedding of the task need, used for the
    semantic sub-score. In simulation it is a seeded synthetic vector; in the live
    pilot it is a real embedding of the task text.
    """

    task_id: str
    required_skills: frozenset[str] = frozenset()
    required_tools: frozenset[str] = frozenset()
    scope: frozenset[str] = frozenset()
    requirement_vector: tuple[float, ...] = ()
    activation_energy: float = 0.20
    priority: float = 1.0


@dataclass(frozen=True)
class Agent:
    """A coding agent described by its role, skills, prompt, tools, and scope.

    ``capability_vector`` is the normalised embedding of the agent descriptor
    (role, skills, and prompt), used for the semantic sub-score. ``capability`` is
    the measured base proficiency in [0, 1] (E4 base). ``successes`` and
    ``attempts`` back the reliability estimate (E4).
    """

    agent_id: str
    role: str = ""
    skills: frozenset[str] = frozenset()
    prompt: str = ""
    tools: frozenset[str] = frozenset()
    permitted_scope: frozenset[str] = frozenset()
    capability_vector: tuple[float, ...] = ()
    capability: float = 1.0
    successes: int = 0
    attempts: int = 0
    latency: float = 1.0
    # E13 self-assessment: the agent reports its own compatibility with a bias
    # (positive is overconfidence) and Gaussian noise. Defaults are perfect
    # calibration, so the self-report equals the true compatibility.
    calibration_bias: float = 0.0
    calibration_noise: float = 0.0
    # The chance the agent attempts an action outside the task scope, used to test
    # the integrity gate as a safety backstop. Default is always in scope.
    out_of_scope_prob: float = 0.0


def _clip01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def cosine(u: Sequence[float], v: Sequence[float]) -> float:
    """Cosine similarity of two vectors, clipped to [0, 1]. Empty vectors give 0."""
    if not u or not v or len(u) != len(v):
        return 0.0
    dot = sum(a * b for a, b in zip(u, v, strict=False))
    nu = math.sqrt(sum(a * a for a in u))
    nv = math.sqrt(sum(b * b for b in v))
    if nu == 0.0 or nv == 0.0:
        return 0.0
    return _clip01(dot / (nu * nv))


def _coverage(required: frozenset[str], held: frozenset[str]) -> float:
    """Fraction of the required set that is held. Empty requirement gives 1."""
    if not required:
        return 1.0
    return len(required & held) / len(required)


def eligible(agent: Agent, task: Task) -> bool:
    """E1, E2: the hard binary gate over required tools and permitted scope.

    Tools and scope are must-haves; skills and domain are graded into compatibility
    rather than vetoed. No eligible agent in the pool means the task is infeasible.
    """
    has_tools = task.required_tools <= agent.tools
    in_scope = task.scope <= agent.permitted_scope
    return has_tools and in_scope


def compatibility(
    agent: Agent,
    task: Task,
    weights: tuple[float, float, float] = (0.50, 0.35, 0.15),
) -> float:
    """E3: the task wrapper compatibility ``c`` in [0, 1].

    Aggregates three measurable sub-scores by a weighted geometric mean, so a
    near-zero on any dimension craters ``c`` (a missing capability should veto):

    - semantic match: cosine of the agent descriptor and the task requirement,
    - skill coverage: fraction of required skills the agent holds,
    - scope fit: fraction of the task scope the agent is permitted for.

    The geometric mean is the documented default; a logistic model calibrated to
    predict success is the validated upgrade (see ``docs/measures.md`` section 3).
    """
    w_sem, w_skill, w_scope = weights
    total = w_sem + w_skill + w_scope
    if total <= 0.0:
        raise ValueError("compatibility weights must sum to a positive value")
    s_sem = cosine(agent.capability_vector, task.requirement_vector)
    s_skill = _coverage(task.required_skills, agent.skills)
    s_scope = _coverage(task.scope, agent.permitted_scope)
    # Weighted geometric mean via logs. Each sub-score is floored (not offset) so a
    # zero is a strong but finite penalty and a perfect score stays exactly 1.
    log_c = (
        w_sem * math.log(max(s_sem, COMPAT_FLOOR))
        + w_skill * math.log(max(s_skill, COMPAT_FLOOR))
        + w_scope * math.log(max(s_scope, COMPAT_FLOOR))
    ) / total
    return _clip01(math.exp(log_c))


def self_reported_compatibility(
    true_c: float,
    bias: float,
    noise: float,
    rng: random.Random,
) -> float:
    """E13: the compatibility the agent believes it has, ``c_hat``.

    The agent does not observe its true fit. It reports ``clip01(true_c + bias +
    noise * N(0, 1))``, where ``bias`` shifts the estimate (positive is
    overconfidence) and ``noise`` scales the random error. With both zero the
    self-report equals the true compatibility, so the default preserves the
    idealised behaviour. Firing and the bid use this self-report; realised
    quality (E12) uses the true compatibility, so miscalibration corrupts the
    allocation without changing the ground truth.
    """
    gap = 0.0 if noise <= 0.0 else noise * rng.gauss(0.0, 1.0)
    return _clip01(true_c + bias + gap)


def reliability(agent: Agent) -> float:
    """E4: Laplace smoothed success ratio ``R = (s + 1) / (n + 2)``."""
    return (agent.successes + 1) / (agent.attempts + 2)


def effective_capability(agent: Agent) -> float:
    """E5: ``C_tilde = C * R``, coupling reliability into capability."""
    return _clip01(agent.capability) * reliability(agent)


def binding_energy(agent: Agent, task: Task) -> float:
    """E6: the selection score ``B = c * C_tilde / max(L, EPS)``.

    Ranks the agents that have cleared activation; it does not gate firing.
    """
    c = compatibility(agent, task)
    return c * effective_capability(agent) / max(agent.latency, EPS)


def activation_drive(agent: Agent, task: Task) -> float:
    """E7: ``Delta = c - Ea``. The barrier is on compatibility, not on B."""
    return compatibility(agent, task) - task.activation_energy


def p_fire(agent: Agent, task: Task, temperature: float = 0.0) -> float:
    """E8: firing probability.

    Deterministic threshold at ``temperature == 0`` (fire iff ``c >= Ea``); the
    Arrhenius soft threshold ``min(1, exp(Delta / T))`` for ``T > 0``.
    """
    delta = activation_drive(agent, task)
    if temperature <= 0.0:
        return 1.0 if delta >= 0.0 else 0.0
    if delta >= 0.0:
        return 1.0
    return math.exp(delta / temperature)


def tie_break_key(agent: Agent, task: Task) -> tuple[float, float, str]:
    """E10 winner ordering key: maximise B, then lower latency, then lower id.

    Use as ``max(candidates, key=lambda a: tie_break_key(a, task))`` after negating
    the fields that should be minimised, or sort with the composite below.
    """
    return (binding_energy(agent, task), -agent.latency, _neg_id(agent.agent_id))


def _neg_id(agent_id: str) -> str:
    # A stable, reversed ordering token so the lexicographically lower identifier
    # wins under max(). Kept simple and deterministic.
    return "".join(chr(255 - ord(ch)) if ord(ch) < 255 else ch for ch in agent_id)


def select_winner(agents: Sequence[Agent], task: Task) -> Agent | None:
    """E9, E10: among agents that fire deterministically, pick the winner.

    Returns None when no eligible agent clears the barrier (the task stalls).
    """
    contenders = [a for a in agents if eligible(a, task) and p_fire(a, task) >= 1.0]
    if not contenders:
        return None
    return max(contenders, key=lambda a: tie_break_key(a, task))


@dataclass(frozen=True)
class GateConfig:
    """Rejection Gate configuration (E11)."""

    acceptance_threshold: float = 0.60
    # Probability the gate detects an out-of-scope action. A real gate (static
    # analysis, a sandbox, a permission check) is not a perfect oracle, so recall
    # below 1 lets some violations slip through and makes the safety result a
    # measured reduction rather than a tautological zero.
    scope_recall: float = 1.0


def gate_admits(
    agent: Agent,
    task: Task,
    in_scope: bool,
    config: GateConfig | None = None,
) -> bool:
    """E11: admit iff reliability clears the threshold and the action is in scope."""
    cfg = config if config is not None else GateConfig()
    return reliability(agent) >= cfg.acceptance_threshold and in_scope
