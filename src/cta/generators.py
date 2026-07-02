"""Seeded population generators for agents and tasks.

Heterogeneity is a first-class control (RQ6, H6). At heterogeneity 0 the agents
are near-interchangeable (capability spread evenly across domains, broad skills);
at heterogeneity 1 they are specialised (capability concentrated on one domain,
narrow skills). Everything is deterministic given the seed, and pure standard
library so the core needs no numerical dependencies.
"""

from __future__ import annotations

import dataclasses
import random

from cta.scoring import Agent, Task


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


def generate_agents(
    n: int,
    n_domains: int,
    heterogeneity: float,
    rng: random.Random,
) -> list[Agent]:
    """Generate ``n`` agents across ``n_domains`` with the given heterogeneity."""
    agents: list[Agent] = []
    for i in range(n):
        home = rng.randrange(n_domains)
        vec = _blend(home, n_domains, heterogeneity, rng)
        if heterogeneity >= 0.5:
            skills = frozenset({f"skill_{home}"})
        else:
            # Broad, near-interchangeable skills when the population is homogeneous.
            skills = frozenset(f"skill_{d}" for d in range(n_domains))
        agents.append(
            Agent(
                agent_id=f"agent_{i}",
                role=f"role_{home}",
                skills=skills,
                prompt=f"agent specialised in domain {home}",
                tools=frozenset({"edit", "test"}),
                permitted_scope=frozenset({"src/**", "tests/**"}),
                capability_vector=vec,
                capability=0.5 + 0.5 * rng.random(),
                # A light positive track record, so a fresh agent starts above the
                # gate threshold (R about 0.71). Unreliable agents are injected
                # separately for the gate ablation (H4).
                successes=4,
                attempts=5,
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


def generate_tasks(
    m: int,
    n_domains: int,
    rng: random.Random,
    activation_energy: float = 0.20,
) -> list[Task]:
    """Generate ``m`` tasks, each anchored to a domain."""
    tasks: list[Task] = []
    for j in range(m):
        domain = rng.randrange(n_domains)
        req = _one_hot(domain, n_domains)
        tasks.append(
            Task(
                task_id=f"task_{j}",
                required_skills=frozenset({f"skill_{domain}"}),
                required_tools=frozenset({"edit", "test"}),
                scope=frozenset({"src/**"}),
                requirement_vector=tuple(req),
                activation_energy=activation_energy,
                priority=1.0,
            )
        )
    return tasks
