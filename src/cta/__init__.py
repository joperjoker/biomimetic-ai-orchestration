"""Chemotactic Task Allocation (CTA).

A decentralised, signal-driven allocation framework for a swarm of coding agents.
Agents self-select tasks: a task wrapper scores an agent's role, skills, and prompt
against the task to yield a compatibility score, an agent may take a task only when
its compatibility reaches the task's activation energy, and a trust gate screens the
winner before it gains write access.

The scoring module in `cta.scoring` implements the operational model defined in
`docs/measures.md` and the formal framework in `docs/paper.md` section 2.2.
"""

from cta.scoring import (
    Agent,
    Task,
    binding_energy,
    compatibility,
    effective_capability,
    eligible,
    gate_admits,
    p_fire,
    reliability,
    tie_break_key,
)

__all__ = [
    "Agent",
    "Task",
    "binding_energy",
    "compatibility",
    "effective_capability",
    "eligible",
    "gate_admits",
    "p_fire",
    "reliability",
    "tie_break_key",
]

__version__ = "0.0.1"
