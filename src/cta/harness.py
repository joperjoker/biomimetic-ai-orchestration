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
from dataclasses import dataclass, field, replace

from cta.baselines import run_central
from cta.engine import run_batch
from cta.generators import (
    generate_agents,
    generate_tasks,
    with_capability_spread,
    with_injected_adversarial,
    with_injected_unreliable,
    with_miscalibration,
    with_track_record,
)
from cta.scoring import Agent, GateConfig, Task, compatibility, eligible
from cta.stats import mean_ci
from cta.temporal import TemporalConfig, run_temporal

CONDITIONS = ("cta", "pull_based", "central_greedy", "central_optimal", "central_best")


@dataclass(frozen=True)
class CellParams:
    n_agents: int = 100
    n_tasks: int = 80
    n_domains: int = 5
    heterogeneity: float = 0.8
    activation_energy: float = 0.20
    temperature: float = 0.0
    observability_k: int | None = 32  # bounded task sampling per agent (A2); None means full
    family: str = "domains"  # generative distribution family (2.7): domains or latent


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
        params.n_agents, params.n_domains, params.heterogeneity, random.Random(seed), params.family
    )
    tasks = generate_tasks(
        params.n_tasks,
        params.n_domains,
        random.Random(seed + 10_000),
        params.activation_energy,
        params.family,
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
        method = {
            "central_greedy": "greedy",
            "central_optimal": "optimal",
            "central_best": "best",
        }[condition]
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
            params = replace(
                protocol.base,
                n_agents=n,
                n_tasks=max(1, int(n * protocol.base.n_tasks / max(1, protocol.base.n_agents))),
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


def calibration_sweep(
    base: CellParams,
    seeds: int,
    bias_values: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3, 0.4),
    noise: float = 0.05,
    modes: tuple[str, ...] = ("raw", "reliability", "true"),
    capability_low: float = 0.2,
) -> dict[str, list[dict[str, object]]]:
    """H7 and H8: vary self-assessment overconfidence and compare selection modes.

    Runs in the documented stress regime (a wide competence spread via
    ``with_capability_spread``), because the choice of competence signal only
    matters when agents genuinely differ in competence. Each agent has an
    informative track record and a self-report drifted by the overconfidence bias.

    For each mode and bias, records mean realised quality, the unmet rate, and the
    per-seed quality values, plus the winners' overconfidence gap (self-report
    minus realised quality) for the ``raw`` mode. ``raw`` ranks on the self-report
    alone; ``reliability`` discounts it by the track record; ``true`` is the
    full-information oracle.
    """
    out: dict[str, list[dict[str, object]]] = {m: [] for m in modes}
    for mode in modes:
        for bias in bias_values:
            q_vals: list[float] = []
            comp_vals: list[float] = []
            unmet: list[float] = []
            gaps: list[float] = []
            briers: list[float] = []
            eces: list[float] = []
            for seed in range(seeds):
                agents = generate_agents(
                    base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed),
                    base.family,
                )
                agents = with_capability_spread(agents, capability_low)
                agents = with_track_record(agents, random.Random(seed + 40_000))
                agents = with_miscalibration(agents, bias, noise, random.Random(seed + 60_000))
                tasks = generate_tasks(
                    base.n_tasks,
                    base.n_domains,
                    random.Random(seed + 10_000),
                    base.activation_energy,
                    base.family,
                )
                res = run_batch(
                    agents,
                    tasks,
                    random.Random(seed + 20_000),
                    condition="cta",
                    temperature=base.temperature,
                    observability_k=base.observability_k,
                    selection_mode=mode,
                ).summary()
                q_vals.append(res["mean_quality"])
                comp_vals.append(res["completion_rate"])
                unmet.append(res["stall_rate"] + res["infeasible_rate"])
                gaps.append(res["overconfidence_gap"])
                briers.append(res["winner_brier"])
                eces.append(res["winner_ece"])
            out[mode].append(
                {
                    "bias": bias,
                    "mean_quality": sum(q_vals) / len(q_vals),
                    "completion_rate": sum(comp_vals) / len(comp_vals),
                    "unmet_rate": sum(unmet) / len(unmet),
                    "overconfidence_gap": sum(gaps) / len(gaps),
                    "winner_brier": sum(briers) / len(briers),
                    "winner_ece": sum(eces) / len(eces),
                    "quality_values": q_vals,
                    "completion_values": comp_vals,
                }
            )
    return out


def track_record_sweep(
    base: CellParams,
    seeds: int,
    windows: tuple[int, ...] = (2, 5, 10, 20, 40),
    bias: float = 0.4,
    noise: float = 0.05,
    capability_low: float = 0.2,
) -> list[dict[str, float]]:
    """How much history the track-record correction needs to work.

    At a fixed high overconfidence, vary the length of the track record (the
    number of prior attempts behind reliability `R`) and record the completion
    recovery of the reliability correction over the raw self-report auction. A
    short history makes `R` a coarse, noisy estimate of competence, so the
    correction is weak; a longer history sharpens `R` and the recovery grows.
    """
    out: list[dict[str, float]] = []
    for window in windows:
        raw_comp: list[float] = []
        rel_comp: list[float] = []
        rel_brier: list[float] = []
        for seed in range(seeds):
            agents = generate_agents(
                base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family
            )
            agents = with_capability_spread(agents, capability_low)
            agents = with_track_record(agents, random.Random(seed + 40_000), attempts=window)
            agents = with_miscalibration(agents, bias, noise, random.Random(seed + 60_000))
            tasks = generate_tasks(
                base.n_tasks,
                base.n_domains,
                random.Random(seed + 10_000),
                base.activation_energy,
                base.family,
            )
            raw = run_batch(
                agents,
                tasks,
                random.Random(seed + 20_000),
                condition="cta",
                observability_k=base.observability_k,
                selection_mode="raw",
            ).summary()
            rel = run_batch(
                agents,
                tasks,
                random.Random(seed + 20_000),
                condition="cta",
                observability_k=base.observability_k,
                selection_mode="reliability",
            ).summary()
            raw_comp.append(raw["completion_rate"])
            rel_comp.append(rel["completion_rate"])
            rel_brier.append(rel["winner_brier"])
        raw_mean = sum(raw_comp) / len(raw_comp)
        rel_mean = sum(rel_comp) / len(rel_comp)
        out.append(
            {
                "window": window,
                "raw_completion": raw_mean,
                "reliability_completion": rel_mean,
                "recovery": rel_mean - raw_mean,
                "reliability_brier": sum(rel_brier) / len(rel_brier),
            }
        )
    return out


def _recovery_at(
    base: CellParams, seeds: int, low: float, bias: float, noise: float = 0.05
) -> float:
    """Mean completion recovery (reliability minus raw) at a spread and a bias."""
    rec: list[float] = []
    for seed in range(seeds):
        agents = generate_agents(
            base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family
        )
        agents = with_capability_spread(agents, low)
        agents = with_track_record(agents, random.Random(seed + 40_000))
        agents = with_miscalibration(agents, bias, noise, random.Random(seed + 60_000))
        tasks = generate_tasks(
            base.n_tasks, base.n_domains, random.Random(seed + 10_000),
            base.activation_energy, base.family,
        )
        raw = run_batch(
            agents, tasks, random.Random(seed + 20_000), condition="cta",
            observability_k=base.observability_k, selection_mode="raw",
        ).summary()["completion_rate"]
        rel = run_batch(
            agents, tasks, random.Random(seed + 20_000), condition="cta",
            observability_k=base.observability_k, selection_mode="reliability",
        ).summary()["completion_rate"]
        rec.append(rel - raw)
    return sum(rec) / len(rec)


def recovery_vs_spread(
    base: CellParams,
    seeds: int,
    lows: tuple[float, ...] = (0.1, 0.2, 0.35, 0.5, 0.7),
    bias: float = 0.4,
) -> list[dict[str, float]]:
    """Sensitivity of the correction's recovery to competence spread.

    Lower ``capability_low`` means a wider competence spread. The recovery of the
    track-record correction should grow as competence varies more, since that is
    where a competence signal matters. This also probes the heterogeneity question
    the pre-registered H6 asks, on the axis where CTA's mechanism can act.
    """
    return [
        {
            "capability_low": low,
            "spread": round(1.0 - low, 3),
            "recovery": _recovery_at(base, seeds, low, bias),
        }
        for low in lows
    ]


def recovery_surface(
    base: CellParams,
    seeds: int,
    biases: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6),
    lows: tuple[float, ...] = (0.1, 0.3, 0.5, 0.7),
) -> dict[str, object]:
    """Recovery over the overconfidence bias by competence spread grid (a surface)."""
    grid = [[_recovery_at(base, seeds, low, bias) for low in lows] for bias in biases]
    return {"biases": list(biases), "lows": list(lows), "recovery": grid}


def reduction_vs_recall(
    base: CellParams,
    seeds: int,
    recalls: tuple[float, ...] = (0.5, 0.7, 0.9, 1.0),
    adversarial_fraction: float = 0.3,
) -> list[dict[str, float]]:
    """Sensitivity of the safety result to the gate's detection recall (H4)."""
    out: list[dict[str, float]] = []
    for r in recalls:
        res = safety_ablation(base, seeds, adversarial_fraction, gate_recall=r)
        on = sum(res["gate_on_violations"]) / len(res["gate_on_violations"])
        off = sum(res["gate_off_violations"]) / len(res["gate_off_violations"])
        out.append(
            {
                "gate_recall": r,
                "gate_on_violations": on,
                "gate_off_violations": off,
                "reduction": 1.0 - on / off if off > 0 else 0.0,
            }
        )
    return out


def safety_ablation(
    base: CellParams,
    seeds: int,
    adversarial_fraction: float = 0.3,
    gate_recall: float = 0.9,
) -> dict[str, list[float]]:
    """H4 (safety): count integrity violations with the gate on and off.

    A fraction of agents are adversarial (likely to act outside the task scope).
    The gate detects an out-of-scope action with recall `gate_recall` below 1, so
    with the gate on the violation count is reduced but not necessarily zero; with
    the gate off every out-of-scope action executes. The result is the measured
    reduction, not a tautological zero.
    """
    on: list[float] = []
    off: list[float] = []
    gate = GateConfig(scope_recall=gate_recall)
    for seed in range(seeds):
        agents = generate_agents(
            base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family
        )
        agents = with_injected_adversarial(
            agents, adversarial_fraction, random.Random(seed + 70_000)
        )
        tasks = generate_tasks(
            base.n_tasks,
            base.n_domains,
            random.Random(seed + 10_000),
            base.activation_energy,
            base.family,
        )
        on_res = run_batch(
            agents,
            tasks,
            random.Random(seed + 20_000),
            condition="cta",
            observability_k=base.observability_k,
            gate=gate,
            gate_enabled=True,
        ).summary()
        off_res = run_batch(
            agents,
            tasks,
            random.Random(seed + 20_000),
            condition="cta",
            observability_k=base.observability_k,
            gate_enabled=False,
        ).summary()
        on.append(on_res["integrity_violations"])
        off.append(off_res["integrity_violations"])
    return {"gate_on_violations": on, "gate_off_violations": off, "gate_recall": [gate_recall]}


def temporal_metrics(base: CellParams, seeds: int) -> dict[str, list[float]]:
    """Run the round-based engine on the base population for temporal measures.

    Returns the per-seed allocation latency, throughput, maximum stall, and
    completion, which the batch engine cannot produce because it has no time axis.
    """
    latency: list[float] = []
    throughput: list[float] = []
    max_stall: list[float] = []
    completion: list[float] = []
    for seed in range(seeds):
        agents = generate_agents(
            base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed)
        )
        tasks = generate_tasks(
            base.n_tasks, base.n_domains, random.Random(seed + 10_000), base.activation_energy
        )
        res = run_temporal(
            agents,
            tasks,
            random.Random(seed + 80_000),
            TemporalConfig(observability_k=base.observability_k),
        ).summary()
        latency.append(res["mean_latency"])
        throughput.append(res["throughput"])
        max_stall.append(res["max_stall"])
        completion.append(res["completion_rate"])
    return {
        "mean_latency": latency,
        "throughput": throughput,
        "max_stall": max_stall,
        "completion_rate": completion,
    }


def _stall_scenario(
    n_agents: int, n_tasks: int, rng: random.Random
) -> tuple[list[Agent], list[Task]]:
    """A controlled scenario where every eligible agent's fit is below the barrier.

    Each agent is a generalist with a uniform capability vector, so its cosine to
    any single-domain task requirement is a fixed 0.5 and its compatibility is
    about 0.707, well under the stall tasks' barrier of 0.85. No agent can clear
    the barrier at first, so the tasks are stalled but feasible: only annealing
    (E14) can lower the barrier enough to resolve them.
    """
    n_domains = 4
    uniform = tuple(1.0 / n_domains for _ in range(n_domains))
    skills = frozenset(f"skill_{d}" for d in range(n_domains))
    agents = [
        Agent(
            agent_id=f"gen_{i}",
            role="generalist",
            skills=skills,
            tools=frozenset({"edit", "test"}),
            permitted_scope=frozenset({"src/**", "tests/**"}),
            capability_vector=uniform,
            capability=0.6 + 0.3 * rng.random(),
            successes=8,
            attempts=10,
            latency=0.5 + rng.random(),
        )
        for i in range(n_agents)
    ]
    tasks = [
        Task(
            task_id=f"stall_{k}",
            required_skills=frozenset({f"skill_{k % n_domains}"}),
            required_tools=frozenset({"edit", "test"}),
            scope=frozenset({"src/**"}),
            requirement_vector=tuple(1.0 if d == k % n_domains else 0.0 for d in range(n_domains)),
            activation_energy=0.85,
        )
        for k in range(n_tasks)
    ]
    return agents, tasks


def annealing_curve(
    base: CellParams,
    seeds: int,
    rates: tuple[float, ...] = (0.0, 0.02, 0.05, 0.1, 0.2),
) -> list[dict[str, float]]:
    """H5: how the annealing rate bounds the stall time of feasible tasks.

    On a controlled stall-prone scenario, sweep the annealing rate and record the
    maximum stall and the unmet rate. At rate zero the barrier never relaxes, the
    feasible tasks are never claimed, and they are unmet with an unbounded stall.
    As the rate rises the barrier drops sooner, so the stall falls and every
    feasible task is resolved. This is the E14 mechanism, measured.
    """
    n_agents = max(4, base.n_agents // 4)
    n_tasks = max(4, base.n_tasks // 4)
    out: list[dict[str, float]] = []
    for rate in rates:
        stalls: list[float] = []
        unmets: list[float] = []
        for seed in range(seeds):
            agents, tasks = _stall_scenario(n_agents, n_tasks, random.Random(seed + 90_000))
            res = run_temporal(
                agents,
                tasks,
                random.Random(seed + 80_000),
                TemporalConfig(annealing=rate > 0.0, anneal_rate=rate),
            ).summary()
            stalls.append(res["max_stall"])
            unmets.append(res["unmet_rate"])
        out.append(
            {
                "rate": rate,
                "max_stall": sum(stalls) / len(stalls),
                "unmet_rate": sum(unmets) / len(unmets),
            }
        )
    return out


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
            params = replace(base, activation_energy=ea, temperature=t)
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
            params = replace(protocol.base, heterogeneity=h)
            rows = run_seeds(condition, params, protocol.seeds)
            agg = aggregate(rows, metric)
            agg["heterogeneity"] = h
            points.append(agg)
        out[condition] = points
    return out
