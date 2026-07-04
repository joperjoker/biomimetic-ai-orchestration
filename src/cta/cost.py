"""A token and dollar cost model for the coordination comparison.

The scaling hypothesis (H1) counts pair evaluations. This turns that count into
money, so the commercial claim rests on a number rather than an assertion. A
central scheduler evaluates every agent-task pair at one node, so its bill grows
as ``N`` times ``M``; a decentralised fleet has each agent evaluate only the
tasks it observes, so the total grows linearly and the busiest node's bill stays
flat. The dollar figures below make that difference explicit.

Prices are representative list rates in USD per million tokens, not a live quote.
They are illustrative tiers (economy, standard, premium) that stand in for the
small, mid, and large model classes; update them to current vendor rates before
quoting an absolute figure. The shape of the comparison, quadratic central versus
linear decentralised, does not depend on the exact prices.
"""

from __future__ import annotations

# (input, output) USD per million tokens. Representative tiers; see module docstring.
PRICING: dict[str, tuple[float, float]] = {
    "economy": (0.25, 1.25),
    "standard": (3.0, 15.0),
    "premium": (15.0, 75.0),
}

# Tokens to score one agent-task pair: read the task spec and the agent descriptor
# (input) and emit a compatibility judgement (output). Deliberately modest, since
# the comparison is about how the count scales, not its absolute size.
EVAL_INPUT_TOKENS = 500
EVAL_OUTPUT_TOKENS = 20


def eval_cost_usd(tier: str = "standard") -> float:
    """USD to evaluate a single agent-task pair at the given price tier."""
    if tier not in PRICING:
        raise ValueError(f"unknown price tier: {tier}")
    in_rate, out_rate = PRICING[tier]
    return (EVAL_INPUT_TOKENS * in_rate + EVAL_OUTPUT_TOKENS * out_rate) / 1_000_000.0


def central_cost_usd(n_agents: int, n_tasks: int, tier: str = "standard") -> float:
    """Coordinator bill: one node scores all ``N`` times ``M`` pairs."""
    return n_agents * n_tasks * eval_cost_usd(tier)


def decentralised_cost_usd(
    n_agents: int, n_tasks: int, observability_k: int | None, tier: str = "standard"
) -> dict[str, float]:
    """Total and busiest-node bill when each agent scores only what it observes.

    Each agent evaluates at most ``observability_k`` tasks (all ``M`` if it is
    None), so the total spend is ``N`` times that per-agent count and the peak
    per-node spend is just that per-agent count, independent of ``N``.
    """
    per_agent_evals = n_tasks if observability_k is None else min(observability_k, n_tasks)
    unit = eval_cost_usd(tier)
    return {
        "total_usd": n_agents * per_agent_evals * unit,
        "per_node_usd": per_agent_evals * unit,
    }


def cost_curve(
    ns: list[int],
    task_ratio: float = 0.8,
    observability_k: int | None = 32,
    tier: str = "standard",
) -> list[dict[str, float]]:
    """Cost against agent count for the central and decentralised schemes.

    ``task_ratio`` sets ``M`` proportional to ``N`` (the sweep's convention), so
    the central bill is quadratic in ``N`` while the decentralised total is linear
    and the decentralised per-node bill is flat.
    """
    out: list[dict[str, float]] = []
    for n in ns:
        m = max(1, int(n * task_ratio))
        dec = decentralised_cost_usd(n, m, observability_k, tier)
        out.append(
            {
                "n_agents": n,
                "n_tasks": m,
                "central_usd": round(central_cost_usd(n, m, tier), 4),
                "decentralised_total_usd": round(dec["total_usd"], 4),
                "decentralised_per_node_usd": round(dec["per_node_usd"], 6),
            }
        )
    return out


def savings_at(
    n_agents: int,
    task_ratio: float = 0.8,
    observability_k: int | None = 32,
    tier: str = "standard",
) -> dict[str, float]:
    """The central-versus-decentralised bill and the multiple saved at one ``N``."""
    m = max(1, int(n_agents * task_ratio))
    central = central_cost_usd(n_agents, m, tier)
    dec = decentralised_cost_usd(n_agents, m, observability_k, tier)["total_usd"]
    return {
        "n_agents": n_agents,
        "central_usd": round(central, 4),
        "decentralised_total_usd": round(dec, 4),
        "savings_multiple": round(central / dec, 2) if dec > 0 else 0.0,
    }
