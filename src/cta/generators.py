"""Seeded population generators for agents and tasks.

Heterogeneity is a first-class control (RQ6, H6). At heterogeneity 0 the agents
are near-interchangeable (capability spread evenly across domains, broad skills);
at heterogeneity 1 they are specialised (capability concentrated on one domain,
narrow skills). Everything is deterministic given the seed, and pure standard
library so the core needs no numerical dependencies.
"""

from __future__ import annotations

import dataclasses
import math
import random

from cta.scoring import Agent, Task

FAMILIES = ("domains", "latent")
"""The generative distribution families, for the generalisability pass (2.7).

``domains`` is the original structure: one-hot task requirements and agents
blended towards a home domain, so compatibility is near-binary. ``latent`` draws
agent and task vectors as softmax-of-Gaussian directions in a continuous latent
space with no discrete skill gate, so compatibility is a smooth function of
alignment. A result that holds under both is not an artefact of the structure.
"""


def _one_hot(index: int, size: int) -> list[float]:
    v = [0.0] * size
    v[index] = 1.0
    return v


def _normalise(v: list[float]) -> tuple[float, ...]:
    total = sum(v)
    if total <= 0.0:
        return tuple(v)
    return tuple(x / total for x in v)


def _blend(
    home: int, n_domains: int, heterogeneity: float, rng: random.Random
) -> tuple[float, ...]:
    """Capability vector: specialised towards the home domain as heterogeneity rises."""
    hot = _one_hot(home, n_domains)
    spread = [rng.random() for _ in range(n_domains)]
    s = sum(spread) or 1.0
    spread = [x / s for x in spread]
    mixed = [heterogeneity * hot[i] + (1.0 - heterogeneity) * spread[i] for i in range(n_domains)]
    return _normalise(mixed)


def _informative_record(capability: float, rng: random.Random, attempts: int = 20) -> int:
    """Successes drawn from the true capability, so R (E4) is a competence signal."""
    return sum(1 for _ in range(attempts) if rng.random() < capability)


def _softmax_direction(dim: int, temperature: float, rng: random.Random) -> tuple[float, ...]:
    """A positive, normalised direction in latent space, peaked as temperature falls."""
    raw = [rng.gauss(0.0, 1.0) for _ in range(dim)]
    t = max(temperature, 1e-3)
    ex = [math.exp(x / t) for x in raw]
    s = sum(ex) or 1.0
    return tuple(e / s for e in ex)


def generate_agents(
    n: int,
    n_domains: int,
    heterogeneity: float,
    rng: random.Random,
    family: str = "domains",
) -> list[Agent]:
    """Generate ``n`` agents. ``family`` selects the generative structure (2.7)."""
    if family not in FAMILIES:
        raise ValueError(f"unknown generator family: {family}")
    if family == "latent":
        return _agents_latent(n, n_domains, heterogeneity, rng)
    return _agents_domains(n, n_domains, heterogeneity, rng)


def _agents_domains(
    n: int, n_domains: int, heterogeneity: float, rng: random.Random
) -> list[Agent]:
    agents: list[Agent] = []
    for i in range(n):
        home = rng.randrange(n_domains)
        vec = _blend(home, n_domains, heterogeneity, rng)
        if heterogeneity >= 0.5:
            skills = frozenset({f"skill_{home}"})
        else:
            # Broad, near-interchangeable skills when the population is homogeneous.
            skills = frozenset(f"skill_{d}" for d in range(n_domains))
        capability = 0.5 + 0.5 * rng.random()
        attempts = 20
        successes = _informative_record(capability, rng, attempts)
        agents.append(
            Agent(
                agent_id=f"agent_{i}",
                role=f"role_{home}",
                skills=skills,
                prompt=f"agent specialised in domain {home}",
                tools=frozenset({"edit", "test"}),
                permitted_scope=frozenset({"src/**", "tests/**"}),
                capability_vector=vec,
                capability=capability,
                successes=successes,
                attempts=attempts,
                latency=0.5 + rng.random(),
            )
        )
    return agents


def _agents_latent(
    n: int, dim: int, heterogeneity: float, rng: random.Random
) -> list[Agent]:
    """Continuous latent structure: no discrete skill gate, smooth cosine fit.

    The agent direction is peaked as heterogeneity rises. Eligibility is by tools
    and scope only (all agents hold them), so compatibility is driven purely by the
    smooth semantic cosine, a structurally different regime from the domains family.
    """
    agents: list[Agent] = []
    temperature = max(0.05, 1.0 - 0.9 * heterogeneity)
    for i in range(n):
        vec = _softmax_direction(dim, temperature, rng)
        capability = 0.5 + 0.5 * rng.random()
        attempts = 20
        successes = _informative_record(capability, rng, attempts)
        agents.append(
            Agent(
                agent_id=f"agent_{i}",
                role="latent",
                skills=frozenset(),
                prompt="latent agent",
                tools=frozenset({"edit", "test"}),
                permitted_scope=frozenset({"src/**", "tests/**"}),
                capability_vector=vec,
                capability=capability,
                successes=successes,
                attempts=attempts,
                latency=0.5 + rng.random(),
            )
        )
    return agents


def with_injected_unreliable(
    agents: list[Agent], fraction: float, rng: random.Random
) -> list[Agent]:
    """Replace a fraction of agents with unreliable ones (poor record, low capability).

    Used for the gate ablation (H4): the gate should deflect these before they win
    and fail, so the gate-on condition should keep quality higher than gate-off.
    """
    out: list[Agent] = []
    for a in agents:
        if rng.random() < fraction:
            out.append(
                dataclasses.replace(a, successes=0, attempts=20, capability=a.capability * 0.3)
            )
        else:
            out.append(a)
    return out


def with_miscalibration(
    agents: list[Agent], bias: float, noise: float, rng: random.Random
) -> list[Agent]:
    """Set a self-assessment bias and noise (E13), concentrated in weak agents.

    Overconfidence is stronger for less capable agents, the documented pattern
    (weaker performers overestimate themselves): the per-agent bias is
    ``bias * (1 - capability)``, so a fully capable agent stays calibrated while a
    weak one inflates its self-report the most. ``bias`` scales the effect and
    ``noise`` is the random error. With ``bias`` and ``noise`` zero the self-report
    equals the true fit. This is what makes miscalibration corrupt the ranking: a
    weak agent can outbid a strong one on self-report alone.
    """
    del rng  # the bias is a deterministic function of capability; no draw needed
    out: list[Agent] = []
    for a in agents:
        cap = 0.0 if a.capability < 0.0 else 1.0 if a.capability > 1.0 else a.capability
        out.append(
            dataclasses.replace(a, calibration_bias=bias * (1.0 - cap), calibration_noise=noise)
        )
    return out


def with_capability_spread(agents: list[Agent], low: float = 0.2) -> list[Agent]:
    """Widen the competence spread by remapping capability to ``[low, 1.0]``.

    The base population has a narrow competence band (about 0.5 to 1.0). Real
    agent fleets are more varied, and a wide competence spread is what makes the
    choice of competence signal matter. This is the documented stress regime for
    the calibration study; it does not change the base population used elsewhere.
    """
    out: list[Agent] = []
    for a in agents:
        cap = 0.0 if a.capability < 0.0 else 1.0 if a.capability > 1.0 else a.capability
        # Base capability sits in [0.5, 1.0]; remap linearly to [low, 1.0].
        stretched = low + (cap - 0.5) / 0.5 * (1.0 - low)
        stretched = 0.0 if stretched < 0.0 else 1.0 if stretched > 1.0 else stretched
        out.append(dataclasses.replace(a, capability=stretched))
    return out


def with_track_record(
    agents: list[Agent], rng: random.Random, attempts: int = 30
) -> list[Agent]:
    """Give each agent a track record that reflects its true capability.

    Draws ``successes`` from ``attempts`` Bernoulli trials with success
    probability equal to the agent's capability, so reliability ``R`` (E4)
    correlates with true competence. This makes the track-record correction
    informative: discounting a bid by ``R`` favours genuinely capable agents,
    which is the mechanism tested against raw self-reports (H8).
    """
    out: list[Agent] = []
    for a in agents:
        p = 0.0 if a.capability < 0.0 else 1.0 if a.capability > 1.0 else a.capability
        successes = sum(1 for _ in range(attempts) if rng.random() < p)
        out.append(dataclasses.replace(a, successes=successes, attempts=attempts))
    return out


def with_injected_adversarial(
    agents: list[Agent], fraction: float, rng: random.Random, out_of_scope_prob: float = 0.9
) -> list[Agent]:
    """Give a fraction of agents a high chance of acting outside the task scope.

    Used to test the integrity gate as a safety backstop (H4): with the gate on
    these out-of-scope actions should be deflected as prevented violations; with
    it off they execute and are recorded as integrity violations.
    """
    out: list[Agent] = []
    for a in agents:
        if rng.random() < fraction:
            out.append(dataclasses.replace(a, out_of_scope_prob=out_of_scope_prob))
        else:
            out.append(a)
    return out


def generate_tasks(
    m: int,
    n_domains: int,
    rng: random.Random,
    activation_energy: float = 0.20,
    family: str = "domains",
) -> list[Task]:
    """Generate ``m`` tasks. ``family`` selects the generative structure (2.7)."""
    if family not in FAMILIES:
        raise ValueError(f"unknown generator family: {family}")
    tasks: list[Task] = []
    for j in range(m):
        if family == "latent":
            # A peaked latent direction; no discrete skill requirement, so fit is
            # the smooth cosine of the agent and task directions.
            req = _softmax_direction(n_domains, 0.3, rng)
            required_skills: frozenset[str] = frozenset()
        else:
            domain = rng.randrange(n_domains)
            req = tuple(_one_hot(domain, n_domains))
            required_skills = frozenset({f"skill_{domain}"})
        tasks.append(
            Task(
                task_id=f"task_{j}",
                required_skills=required_skills,
                required_tools=frozenset({"edit", "test"}),
                scope=frozenset({"src/**"}),
                requirement_vector=req,
                activation_energy=activation_energy,
                priority=1.0,
            )
        )
    return tasks
