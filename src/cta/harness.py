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
from cta.generators import generate_agents, generate_tasks, with_injected_unreliable
from cta.scoring import Task, compatibility, eligible
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
    observability_k: int | None = 32  # bounded task sampling per agent (A2); None means full


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
            agents,
            tasks,
            exec_rng,
            condition=condition,
            temperature=params.temperature,
            observability_k=params.observability_k,
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
                observability_k=protocol.base.observability_k,
            )
            rows = run_seeds(condition, params, protocol.seeds)
            agg = aggregate(rows, metric)
            agg["n_agents"] = n
            points.append(agg)
        out[condition] = points
    return out


def gate_ablation(
    base: CellParams, seeds: int, unreliable_fraction: float = 0.4
) -> dict[str, list[float]]:
    """H4: compare mean quality with the gate on and off under injected unreliability."""
    on_q: list[float] = []
    off_q: list[float] = []
    for seed in range(seeds):
        agents = generate_agents(
            base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed)
        )
        agents = with_injected_unreliable(
            agents, unreliable_fraction, random.Random(seed + 50_000)
        )
        tasks = generate_tasks(
            base.n_tasks, base.n_domains, random.Random(seed + 10_000), base.activation_energy
        )
        on = run_batch(
            agents, tasks, random.Random(seed + 20_000), condition="cta", gate_enabled=True
        ).summary()
        off = run_batch(
            agents, tasks, random.Random(seed + 20_000), condition="cta", gate_enabled=False
        ).summary()
        on_q.append(on["mean_quality"])
        off_q.append(off["mean_quality"])
    return {"gate_on_quality": on_q, "gate_off_quality": off_q}


def feasibility_check(base: CellParams, seed: int = 0) -> dict[str, float]:
    """H3: check that the engine labels infeasible and stalled tasks correctly.

    Builds a mixed task set with known ground truth (some require a tool no agent
    has; some carry an unreachable activation energy) and compares the labels the
    engine assigns against the truth.
    """
    agents = generate_agents(base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed))
    feasible = generate_tasks(base.n_tasks, base.n_domains, random.Random(seed + 1), 0.2)
    infeasible = [
        Task(
            task_id=f"infeasible_{k}",
            required_tools=frozenset({"deploy"}),  # no agent holds this tool
            scope=frozenset({"src/**"}),
            requirement_vector=tuple(1.0 if d == 0 else 0.0 for d in range(base.n_domains)),
            activation_energy=0.2,
        )
        for k in range(10)
    ]
    stalled = [
        Task(
            task_id=f"stalled_{k}",
            required_tools=frozenset({"edit", "test"}),
            scope=frozenset({"src/**"}),
            requirement_vector=tuple(1.0 if d == 0 else 0.0 for d in range(base.n_domains)),
            activation_energy=0.999,  # unreachable barrier
        )
        for k in range(10)
    ]
    tasks = feasible + infeasible + stalled
    result = run_batch(agents, tasks, random.Random(seed + 2), condition="cta")
    label = {o.task_id: o.status for o in result.outcomes}

    def truth(task: Task) -> str:
        elig = [a for a in agents if eligible(a, task)]
        if not elig:
            return "INFEASIBLE"
        if max(compatibility(a, task) for a in elig) < task.activation_energy:
            return "STALLED"
        return "FEASIBLE"

    inf_correct = sum(1 for t in infeasible if label[t.task_id] == "INFEASIBLE" == truth(t))
    stall_correct = sum(1 for t in stalled if label[t.task_id] == "STALLED" == truth(t))
    return {
        "infeasible_recall": inf_correct / len(infeasible),
        "stalled_recall": stall_correct / len(stalled),
    }


def stability_grid(
    base: CellParams,
    seeds: int,
    ea_values: tuple[float, ...] = (0.1, 0.2, 0.3, 0.5, 0.7),
    t_values: tuple[float, ...] = (0.0, 0.1, 0.3),
) -> list[dict[str, float]]:
    """H5: sweep the activation barrier and temperature, recording stall and quality."""
    grid: list[dict[str, float]] = []
    for ea in ea_values:
        for t in t_values:
            params = CellParams(
                n_agents=base.n_agents,
                n_tasks=base.n_tasks,
                n_domains=base.n_domains,
                heterogeneity=base.heterogeneity,
                activation_energy=ea,
                temperature=t,
            )
            rows = run_seeds("cta", params, seeds)
            stall = sum(r["stall_rate"] + r["infeasible_rate"] for r in rows) / len(rows)
            quality = sum(r["mean_quality"] for r in rows) / len(rows)
            grid.append(
                {
                    "activation_energy": ea,
                    "temperature": t,
                    "unmet_rate": stall,
                    "mean_quality": quality,
                }
            )
    return grid


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
                observability_k=protocol.base.observability_k,
            )
            rows = run_seeds(condition, params, protocol.seeds)
            agg = aggregate(rows, metric)
            agg["heterogeneity"] = h
            points.append(agg)
        out[condition] = points
    return out
