"""A minimal, runnable proof of concept for Chemotactic Task Allocation (P2.6).

A prospective user can run this on a small fleet to watch the mechanism work end
to end: agents self-select tasks through the calibrated, reliability-weighted bid,
the integrity gate screens each winner before it acts, and the coordinator cost a
central scheduler would have paid is reported against the decentralised cost. It
runs offline and deterministically on the simulation engine, so it needs no model
calls or budget. Pointing the same flow at real Claude Code subagents is the
follow-up (future work, P3.4).
"""

from __future__ import annotations

import random

from cta.cost import central_cost_usd, decentralised_cost_usd
from cta.engine import run_batch
from cta.generators import generate_agents, generate_tasks, with_injected_adversarial


def run_poc(
    seed: int = 0,
    n_agents: int = 8,
    n_tasks: int = 8,
    n_domains: int = 4,
    adversarial_fraction: float = 0.5,
) -> dict:
    """Run the demo scenario and return a summary a caller can print or assert.

    Half the fleet is adversarial (prone to act outside a task's scope), so the
    integrity gate has something to catch. Running the same allocation with the
    gate on and off shows how many out-of-scope actions it prevents.
    """
    agents = generate_agents(n_agents, n_domains, 0.8, random.Random(seed))
    agents = with_injected_adversarial(
        agents, adversarial_fraction, random.Random(seed + 70_000)
    )
    tasks = generate_tasks(n_tasks, n_domains, random.Random(seed + 10_000), 0.2)

    gated = run_batch(
        agents, tasks, random.Random(seed + 20_000), condition="cta", gate_enabled=True
    )
    ungated = run_batch(
        agents, tasks, random.Random(seed + 20_000), condition="cta", gate_enabled=False
    )
    on = gated.summary()
    off = ungated.summary()

    allocation = [
        {"task": o.task_id, "winner": o.winner, "status": o.status} for o in gated.outcomes
    ]
    # The coordinator's bill is the honest comparison: a central scheduler scores
    # all N times M pairs at one node, while the busiest decentralised node scores
    # only what one agent observes. Cost is analytic, so we report it at a
    # realistic bounded observability rather than from this tiny run.
    observability_k = max(1, n_tasks // 2)
    central = central_cost_usd(n_agents, n_tasks)
    per_node = decentralised_cost_usd(n_agents, n_tasks, observability_k=observability_k)[
        "per_node_usd"
    ]
    return {
        "n_agents": n_agents,
        "n_tasks": n_tasks,
        "allocation": allocation,
        "completed": int(on["completed"]),
        "prevented_violations": int(off["integrity_violations"] - on["integrity_violations"]),
        "central_cost_usd": round(central, 4),
        "decentralised_per_node_usd": round(per_node, 6),
        "savings_multiple": round(central / per_node, 2) if per_node else 0.0,
    }
