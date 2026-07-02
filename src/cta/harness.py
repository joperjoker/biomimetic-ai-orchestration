"""The experiment harness: run conditions across seeds and sweeps.

One function runs a single (condition, parameters, seed) cell; helpers repeat it
across seeds and sweep a variable. The four conditions share the same scoring, so
only the coordination differs. Results are plain dictionaries, ready for the
statistics and report layers.

Conditions: ``cta`` and ``pull_based`` (decentralised, via the event loop) and
``central_greedy`` and ``central_optimal`` (the control schedulers).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from cta.baselines import run_central
from cta.engine import run_batch
from cta.generators import generate_agents, generate_tasks
from cta.stats import mean_ci

CONDITIONS = ("cta", "pull_based", "central_greedy", "central_optimal")


@dataclass(frozen=True)
class CellParams:
    n_agents: int = 100
    n_tasks: int = 80
    n_domains: int = 5
    heterogeneity: float = 0.8
    activation_energy: float = 0.20
    temperature: float = 0.0


@dataclass
class Protocol:
    """A small pre-registered protocol for the autonomous run."""

    seeds: int = 20
    base: CellParams = field(default_factory=CellParams)
    scaling_n: tuple[int, ...] = (50, 100, 200, 500, 1000, 2000)
    heterogeneity_grid: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)


def run_cell(condition: str, params: CellParams, seed: int) -> dict[str, float]:
    """Run one condition once, deterministically for the given seed."""
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition: {condition}")
    agents = generate_agents(
        params.n_agents, params.n_domains, params.heterogeneity, random.Random(seed)
    )
    tasks = generate_tasks(
        params.n_tasks, params.n_domains, random.Random(seed + 10_000), params.activation_energy
    )
    exec_rng = random.Random(seed + 20_000)
    if condition in ("cta", "pull_based"):
        result = run_batch(
            agents, tasks, exec_rng, condition=condition, temperature=params.temperature
        )
        summary = result.summary()
    else:
        method = "greedy" if condition == "central_greedy" else "optimal"
        summary = run_central(agents, tasks, exec_rng, method=method)
    summary["condition"] = condition
    summary["seed"] = seed
    return summary


def run_seeds(condition: str, params: CellParams, seeds: int) -> list[dict[str, float]]:
    """Run a condition across ``seeds`` replications."""
    return [run_cell(condition, params, seed) for seed in range(seeds)]


def aggregate(rows: list[dict[str, float]], metric: str) -> dict[str, float]:
    """Mean and 95 per cent confidence interval of a metric across replications."""
    values = [r[metric] for r in rows if metric in r]
    mean, lo, hi = mean_ci(values)
    return {"metric": metric, "mean": mean, "ci_low": lo, "ci_high": hi, "n": len(values)}


def scaling_sweep(
    conditions: tuple[str, ...], protocol: Protocol, metric: str = "mean_quality"
) -> dict[str, list[dict[str, float]]]:
    """Sweep the agent count for each condition, returning aggregated points."""
    out: dict[str, list[dict[str, float]]] = {}
    for condition in conditions:
        points: list[dict[str, float]] = []
        for n in protocol.scaling_n:
            params = CellParams(
                n_agents=n,
                n_tasks=max(1, int(n * protocol.base.n_tasks / max(1, protocol.base.n_agents))),
                n_domains=protocol.base.n_domains,
                heterogeneity=protocol.base.heterogeneity,
                activation_energy=protocol.base.activation_energy,
                temperature=protocol.base.temperature,
            )
            rows = run_seeds(condition, params, protocol.seeds)
            agg = aggregate(rows, metric)
            agg["n_agents"] = n
            points.append(agg)
        out[condition] = points
    return out


def heterogeneity_sweep(
    conditions: tuple[str, ...], protocol: Protocol, metric: str = "mean_quality"
) -> dict[str, list[dict[str, float]]]:
    """Sweep agent heterogeneity for each condition (RQ6, H6)."""
    out: dict[str, list[dict[str, float]]] = {}
    for condition in conditions:
        points: list[dict[str, float]] = []
        for h in protocol.heterogeneity_grid:
            params = CellParams(
                n_agents=protocol.base.n_agents,
                n_tasks=protocol.base.n_tasks,
                n_domains=protocol.base.n_domains,
                heterogeneity=h,
                activation_energy=protocol.base.activation_energy,
                temperature=protocol.base.temperature,
            )
            rows = run_seeds(condition, params, protocol.seeds)
            agg = aggregate(rows, metric)
            agg["heterogeneity"] = h
            points.append(agg)
        out[condition] = points
    return out
