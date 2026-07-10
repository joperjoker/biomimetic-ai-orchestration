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

from cta.baselines import coordinator_cost, run_central, run_central_bounded
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

CONDITIONS = (
    "cta",
    "pull_based",
    "central_greedy",
    "central_optimal",
    "central_best",
    "central_bounded",
)

# Load fields that run_central reports analytically (N times M), independent of
# the assignment; a sweep reading only these can skip computing the assignment.
LOAD_METRICS = frozenset(
    {"coordinator_work", "total_work", "peak_agent_work", "peak_store_load", "peak_per_node"}
)


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
    # Bounded-information central baseline (P1.0): how stale the coordinator's
    # reliability estimate is, and how much observation noise it adds to reports.
    central_staleness: float = 0.0
    central_report_noise: float = 0.0


@dataclass
class Protocol:
    """A small pre-registered protocol for the autonomous run."""

    seeds: int = 20
    base: CellParams = field(default_factory=CellParams)
    scaling_n: tuple[int, ...] = (50, 100, 200, 500, 1000, 2000, 5000, 10000)
    heterogeneity_grid: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)
    # The scaling curve measures peak per-node load, which is bounded and
    # low-variance for the decentralised conditions (at most observability_k) and
    # analytic for the central ones, so it needs far fewer seeds than the quality
    # hypotheses, keeping the large-N tail tractable.
    scaling_seeds: int = 5


def run_cell(
    condition: str, params: CellParams, seed: int, quality: bool = True
) -> dict[str, float]:
    """Run one condition once, deterministically for the given seed.

    ``quality=False`` is the load-only fast path for the central conditions: the
    analytic load fields are returned without computing the assignment. It has
    no effect on the decentralised conditions, which must run to be measured.
    """
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
    elif condition == "central_bounded":
        if not quality:
            summary = {
                "tasks": len(tasks),
                "assigned": 0,
                "completed": 0,
                "infeasible_rate": 0.0,
                "mean_quality": 0.0,
                **coordinator_cost(agents, tasks),
                "method": "bounded-load-only",
            }
        else:
            summary = run_central_bounded(
                agents,
                tasks,
                exec_rng,
                staleness=params.central_staleness,
                noise=params.central_report_noise,
            )
    else:
        method = {
            "central_greedy": "greedy",
            "central_optimal": "optimal",
            "central_best": "best",
        }[condition]
        summary = run_central(agents, tasks, exec_rng, method=method, quality=quality)
    summary["condition"] = condition
    summary["seed"] = seed
    return summary


def run_seeds(
    condition: str, params: CellParams, seeds: int, quality: bool = True
) -> list[dict[str, float]]:
    """Run a condition across ``seeds`` replications."""
    return [run_cell(condition, params, seed, quality=quality) for seed in range(seeds)]


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
        # Central load fields are analytic, so when the sweep reads only a load
        # metric the assignment need not be computed; this unlocks large N.
        load_only = condition.startswith("central") and metric in LOAD_METRICS
        points: list[dict[str, float]] = []
        for n in protocol.scaling_n:
            params = replace(
                protocol.base,
                n_agents=n,
                n_tasks=max(1, int(n * protocol.base.n_tasks / max(1, protocol.base.n_agents))),
            )
            rows = run_seeds(condition, params, protocol.scaling_seeds, quality=not load_only)
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


def learning_curve(
    base: CellParams,
    seeds: int,
    rounds: int = 12,
    bias: float = 0.3,
    noise: float = 0.05,
    modes: tuple[str, ...] = ("reliability", "raw", "true"),
    capability_low: float = 0.2,
) -> dict[str, object]:
    """H13: does a persistent, accumulating track record make the allocation self-improve?

    Starting from an uninformative track record (no history, so reliability sits at
    the 0.5 prior for every agent), a heterogeneous, miscalibrated population meets a
    stream of comparable task batches. After each round the winners' realised
    outcomes update the track record, so the next round's reliability-weighted
    selection carries a sharper competence signal. Under ``reliability`` mean
    realised quality should climb round over round toward the full-information oracle
    (``true``); under ``raw``, whose bid has no track-record term, it should stay
    flat, which isolates the improvement to the accumulating memory rather than to
    the task stream. This reuses the batch engine round by round rather than changing
    the engine, mirroring ``strategic_adversary``.
    """

    def series(mode: str) -> tuple[list[float], list[float]]:
        comp_round: list[list[float]] = [[] for _ in range(rounds)]
        qual_round: list[list[float]] = [[] for _ in range(rounds)]
        for seed in range(seeds):
            agents0 = generate_agents(
                base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family,
            )
            agents0 = with_capability_spread(agents0, capability_low)
            agents0 = with_miscalibration(agents0, bias, noise, random.Random(seed + 60_000))
            # Uninformative starting record: reliability begins at the 0.5 prior for all.
            record = {a.agent_id: [0, 0] for a in agents0}
            for r in range(rounds):
                current = [
                    replace(a, successes=record[a.agent_id][0], attempts=record[a.agent_id][1])
                    for a in agents0
                ]
                tasks = generate_tasks(
                    base.n_tasks, base.n_domains, random.Random(seed + 1000 * r),
                    base.activation_energy, base.family,
                )
                res = run_batch(
                    current, tasks, random.Random(seed + 50_000 + r), condition="cta",
                    temperature=base.temperature, observability_k=base.observability_k,
                    selection_mode=mode, gate_enabled=False,
                )
                s = res.summary()
                comp_round[r].append(s["completion_rate"])
                qual_round[r].append(s["mean_quality"])
                # Update the track record from realised outcomes (the memory), applied
                # under every mode so the record accumulates identically; only the bid
                # differs, so any divergence is due to using the record, not building it.
                for o in res.outcomes:
                    if o.winner is not None:
                        record[o.winner][1] += 1
                        if o.status == "COMPLETED":
                            record[o.winner][0] += 1
        return (
            [sum(x) / len(x) for x in comp_round],
            [sum(x) / len(x) for x in qual_round],
        )

    completion: dict[str, list[float]] = {}
    quality: dict[str, list[float]] = {}
    for m in modes:
        completion[m], quality[m] = series(m)

    # Headline is the completion rate: with a persistent record the allocation
    # routes more tasks to agents that actually complete them, so completion climbs.
    rel = completion.get("reliability", [])
    raw = completion.get("raw", [])
    oracle = completion.get("true", [])
    reliability_lift = (rel[-1] - rel[0]) if rel else 0.0
    raw_lift = (raw[-1] - raw[0]) if raw else 0.0
    gap0 = (oracle[0] - rel[0]) if (oracle and rel) else 0.0
    gap_closed = (reliability_lift / gap0) if gap0 > 1e-9 else 0.0
    return {
        "rounds": rounds,
        "bias": bias,
        "modes": list(modes),
        "completion": completion,
        "quality": quality,
        "reliability_lift": reliability_lift,
        "raw_lift": raw_lift,
        "final_gap_to_oracle": (oracle[-1] - rel[-1]) if (oracle and rel) else 0.0,
        "gap_closed": gap_closed,
    }


def strategic_adversary(
    base: CellParams,
    seeds: int,
    rounds: int = 8,
    adversary_fraction: float = 0.15,
    bias: float = 0.6,
    low_capability: float = 0.15,
) -> dict[str, object]:
    """P3.2: does the track record demote an agent that games its self-report?

    A strategic adversary inflates its self-report to win bids (high overconfidence
    bias) while being genuinely incompetent (low capability), and it starts with a
    clean record so it wins early. Over sequential rounds the record is updated from
    each winner's realised outcomes, so the adversary's reliability falls as it
    fails, and reliability-weighted selection should demote it. This reuses the
    batch engine round by round rather than changing the engine; the ``raw`` share
    is recorded for contrast (raw selection has no track-record feedback). Returns
    the adversary win share per round under each selection mode and the decay.
    """
    n_adversaries = max(1, int(base.n_agents * adversary_fraction))

    def share_series(mode: str) -> list[float]:
        per_round: list[list[float]] = [[] for _ in range(rounds)]
        for seed in range(seeds):
            agents = generate_agents(
                base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family
            )
            agents = [
                replace(
                    a,
                    calibration_bias=bias if i < n_adversaries else a.calibration_bias,
                    capability=low_capability if i < n_adversaries else a.capability,
                    successes=18 if i < n_adversaries else a.successes,
                    attempts=20,
                )
                for i, a in enumerate(agents)
            ]
            adversaries = {a.agent_id for a in agents[:n_adversaries]}
            record = {a.agent_id: [a.successes, a.attempts] for a in agents}
            for r in range(rounds):
                current = [
                    replace(a, successes=record[a.agent_id][0], attempts=record[a.agent_id][1])
                    for a in agents
                ]
                tasks = generate_tasks(
                    base.n_tasks, base.n_domains, random.Random(seed + 1000 * r),
                    base.activation_energy, base.family,
                )
                res = run_batch(
                    current, tasks, random.Random(seed + 20_000 + r), condition="cta",
                    selection_mode=mode,
                )
                won = [o for o in res.outcomes if o.winner is not None]
                adv_wins = sum(1 for o in won if o.winner in adversaries)
                per_round[r].append(adv_wins / len(won) if won else 0.0)
                for o in won:
                    record[o.winner][1] += 1
                    if o.status == "COMPLETED":
                        record[o.winner][0] += 1
        return [sum(x) / len(x) for x in per_round]

    reliability_share = share_series("reliability")
    raw_share = share_series("raw")
    return {
        "rounds": rounds,
        "reliability_share": reliability_share,
        "raw_share": raw_share,
        "reliability_decay": reliability_share[0] - reliability_share[-1],
    }


def sandbagging_adversary(
    base: CellParams,
    seeds: int,
    rounds: int = 10,
    honest_rounds: int = 5,
    adversary_fraction: float = 0.15,
    honest_capability: float = 0.9,
    defect_capability: float = 0.1,
    defect_bias: float = 0.6,
    window: int = 6,
) -> dict[str, object]:
    """Reputation gaming: an adversary builds a clean track record, then defects.

    Unlike the naive self-report inflater (``strategic_adversary``), a sandbagging
    adversary does genuine work for ``honest_rounds`` to earn a high reliability,
    then defects, inflating its self-report while its realised work fails. The plain
    cumulative track record is slow to react because the old honest successes
    dilute the new failures, so the adversary exploits its reputation for a window
    of rounds. We run the identical scenario under two reliability accountings,
    ``cumulative`` (all history) and ``windowed`` (only the last ``window``
    outcomes, a recency weighting), and report the adversary win share and the wins
    it fails (the exploitation damage) per round, and the total damage after the
    defect point. The recency window is the lever that shortens the exploitation.
    """
    n_adv = max(1, int(base.n_agents * adversary_fraction))

    def series(accounting: str) -> tuple[list[float], list[float]]:
        share: list[list[float]] = [[] for _ in range(rounds)]
        fails: list[list[float]] = [[] for _ in range(rounds)]
        for seed in range(seeds):
            agents0 = generate_agents(
                base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family
            )
            adversaries = {a.agent_id for a in agents0[:n_adv]}
            hist: dict[str, list[int]] = {a.agent_id: [1, 1, 0] for a in agents0}
            for r in range(rounds):
                defect = r >= honest_rounds
                current = []
                for a in agents0:
                    h = hist[a.agent_id]
                    recent = h if accounting == "cumulative" else h[-window:]
                    succ, att = sum(recent), len(recent)
                    if a.agent_id in adversaries:
                        current.append(replace(
                            a, successes=succ, attempts=att,
                            capability=defect_capability if defect else honest_capability,
                            calibration_bias=defect_bias if defect else 0.0,
                        ))
                    else:
                        current.append(replace(a, successes=succ, attempts=att))
                tasks = generate_tasks(
                    base.n_tasks, base.n_domains, random.Random(seed + 1000 * r),
                    base.activation_energy, base.family,
                )
                res = run_batch(
                    current, tasks, random.Random(seed + 30_000 + r),
                    condition="cta", selection_mode="reliability",
                )
                won = [o for o in res.outcomes if o.winner is not None]
                adv_won = [o for o in won if o.winner in adversaries]
                share[r].append(len(adv_won) / len(won) if won else 0.0)
                fails[r].append(sum(1 for o in adv_won if o.status != "COMPLETED"))
                for o in won:
                    hist[o.winner].append(1 if o.status == "COMPLETED" else 0)
        mean = lambda xs: [sum(x) / len(x) for x in xs]  # noqa: E731
        return mean(share), mean(fails)

    cum_share, cum_fail = series("cumulative")
    win_share, win_fail = series("windowed")
    return {
        "rounds": rounds,
        "honest_rounds": honest_rounds,
        "window": window,
        "cumulative_share": cum_share,
        "windowed_share": win_share,
        "cumulative_fail": cum_fail,
        "windowed_fail": win_fail,
        "cumulative_damage": sum(cum_fail[honest_rounds:]),
        "windowed_damage": sum(win_fail[honest_rounds:]),
    }


def exposure_cap_defense(
    base: CellParams,
    seeds: int,
    honest_rounds: int = 3,
    caps: tuple[int | None, ...] = (None, 1, 3),
    adversary_fraction: float = 0.15,
    honest_capability: float = 0.9,
    defect_capability: float = 0.1,
    defect_bias: float = 0.6,
) -> dict[str, object]:
    """Bound the blast radius of the first defection with an exposure cap.

    No reactive track record can pre-empt a previously honest agent's first
    defection, so the residual damage is what that agent does in the round it
    defects, before its reliability updates. An exposure cap, a defence-in-depth
    limit on how many tasks any single agent may win per round, bounds that blast
    radius: even a fully trusted agent that turns can only damage a capped number
    of tasks before the recency window and the gate react. This measures the failed
    adversary wins in the first defect round under several caps (``None`` is the
    unthrottled baseline), so the bound is shown rather than asserted.
    """
    n_adv = max(1, int(base.n_agents * adversary_fraction))
    per_cap: dict[str, float] = {}
    for cap in caps:
        damages: list[float] = []
        for seed in range(seeds):
            agents0 = generate_agents(
                base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family
            )
            adversaries = {a.agent_id for a in agents0[:n_adv]}
            hist: dict[str, list[int]] = {a.agent_id: [1, 1, 0] for a in agents0}
            for r in range(honest_rounds + 1):
                defect = r == honest_rounds
                current = []
                for a in agents0:
                    h = hist[a.agent_id]
                    if a.agent_id in adversaries:
                        current.append(replace(
                            a, successes=sum(h), attempts=len(h),
                            capability=defect_capability if defect else honest_capability,
                            calibration_bias=defect_bias if defect else 0.0,
                        ))
                    else:
                        current.append(replace(a, successes=sum(h), attempts=len(h)))
                tasks = generate_tasks(
                    base.n_tasks, base.n_domains, random.Random(seed + 1000 * r),
                    base.activation_energy, base.family,
                )
                res = run_batch(
                    current, tasks, random.Random(seed + 40_000 + r),
                    condition="cta", selection_mode="reliability", exposure_cap=cap,
                )
                won = [o for o in res.outcomes if o.winner is not None]
                if defect:
                    damages.append(
                        sum(1 for o in won if o.winner in adversaries and o.status != "COMPLETED")
                    )
                for o in won:
                    hist[o.winner].append(1 if o.status == "COMPLETED" else 0)
        per_cap[str(cap)] = sum(damages) / len(damages) if damages else 0.0
    return {
        "honest_rounds": honest_rounds,
        "n_adversaries": n_adv,
        "caps": [str(c) for c in caps],
        "first_defect_damage": per_cap,
    }


def fitted_calibration_recovery(
    base: CellParams, seeds: int, mix: dict[str, float] | None = None
) -> dict[str, float]:
    """H8 under measured miscalibration: recovery when the bias is not hand-picked.

    The calibration sweep injects one chosen overconfidence bias. This repeats the
    raw-versus-reliability comparison on a population whose per-agent calibration is
    sampled from the measured MarketBench archetype mixture instead, so the recovery
    is shown not to be an artefact of the injected bias shape. Returns the raw and
    reliability completion and their difference.
    """
    from cta.realism import with_fitted_miscalibration

    raw_vals: list[float] = []
    rel_vals: list[float] = []
    for seed in range(seeds):
        agents = generate_agents(
            base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family
        )
        agents = with_capability_spread(agents, 0.2)
        agents = with_track_record(agents, random.Random(seed + 40_000))
        agents = with_fitted_miscalibration(agents, random.Random(seed + 60_000), mix)
        tasks = generate_tasks(
            base.n_tasks, base.n_domains, random.Random(seed + 10_000),
            base.activation_energy, base.family,
        )
        raw = run_batch(
            agents, tasks, random.Random(seed + 20_000), condition="cta", selection_mode="raw"
        ).summary()
        rel = run_batch(
            agents, tasks, random.Random(seed + 20_000), condition="cta",
            selection_mode="reliability",
        ).summary()
        raw_vals.append(raw["completion_rate"])
        rel_vals.append(rel["completion_rate"])
    raw_mean = sum(raw_vals) / len(raw_vals)
    rel_mean = sum(rel_vals) / len(rel_vals)
    return {
        "raw_completion": raw_mean,
        "reliability_completion": rel_mean,
        "recovery": rel_mean - raw_mean,
    }


def bounded_vs_cta(
    base: CellParams,
    seeds: int,
    staleness_values: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
    bias: float = 0.3,
    noise: float = 0.05,
    report_noise: float = 0.0,
    capability_low: float = 0.2,
) -> list[dict[str, object]]:
    """H6, refit: CTA against an information-bounded central scheduler (P1.0).

    The full-information ``central_best`` reference is unbeatable by construction,
    so H6 (CTA matches or beats central coordination) is only a fair question
    against a central scheduler that, like any real one, allocates from
    self-reports and a possibly stale reliability table. Both conditions face the
    same miscalibrated, competence-spread fleet with the same track record, so the
    comparison isolates centralised versus decentralised coordination, not the
    information each is handed. Staleness is the coordinator's structural
    disadvantage: a central table is synchronised in batches and lags, whereas a
    decentralised agent acts on its own current record.

    Returns, per staleness level, the mean realised quality of CTA (reliability
    selection) and of the bounded central, their per-seed values for a
    significance test, and CTA's advantage. At zero staleness the central
    scheduler has fresh information and the two are close; as staleness rises CTA's
    local correction pulls ahead.
    """
    out: list[dict[str, object]] = []
    for stale in staleness_values:
        cta_q: list[float] = []
        bnd_q: list[float] = []
        for seed in range(seeds):
            agents = generate_agents(
                base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family
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
            cta = run_batch(
                agents,
                tasks,
                random.Random(seed + 20_000),
                condition="cta",
                temperature=base.temperature,
                observability_k=base.observability_k,
                selection_mode="reliability",
            ).summary()
            bnd = run_central_bounded(
                agents, tasks, random.Random(seed + 20_000), staleness=stale, noise=report_noise
            )
            cta_q.append(cta["mean_quality"])
            bnd_q.append(bnd["mean_quality"])
        cta_mean = sum(cta_q) / len(cta_q)
        bnd_mean = sum(bnd_q) / len(bnd_q)
        out.append(
            {
                "staleness": stale,
                "cta_quality": cta_mean,
                "bounded_quality": bnd_mean,
                "advantage": cta_mean - bnd_mean,
                "cta_values": cta_q,
                "bounded_values": bnd_q,
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


# The biomimetic mechanisms toggled in the ablation, mapped to their biological
# source: the activation barrier (a response threshold, from chemistry and the
# division of labour) and the integrity gate (a scope block, from the zona
# pellucida). The reliability-weighted bid (cryptic female choice) is the shared
# auction underneath, held on in every arm so the ablation isolates the other two.
ABLATION_ARMS: dict[str, tuple[bool, bool]] = {
    "full": (True, True),
    "minus_barrier": (False, True),
    "minus_gate": (True, False),
    "plain_auction": (False, False),
}


def biomimicry_ablation(
    base: CellParams,
    seeds: int,
    bias: float = 0.3,
    noise: float = 0.05,
    capability_low: float = 0.2,
    adversarial_fraction: float = 0.3,
    gate_recall: float = 0.9,
) -> dict[str, dict[str, object]]:
    """Isolate the contribution of each biological mechanism (P2.4).

    Runs four arms over one combined stress regime, a miscalibrated,
    competence-spread fleet that also contains adversarial agents, so quality,
    unmet work, and integrity violations are all meaningful at once. Every arm
    uses the reliability-weighted bid; the arms differ only in whether the
    activation barrier and the integrity gate are present. Removing the barrier is
    modelled by dropping the tasks' activation energy to zero (every agent may
    fire); removing the gate lets an out-of-scope action execute. The point is
    attribution, not a foregone win: if a mechanism does not move its metric, the
    result says so.
    """
    gate = GateConfig(scope_recall=gate_recall)
    out: dict[str, dict[str, object]] = {}
    for name, (barrier, gate_on) in ABLATION_ARMS.items():
        q: list[float] = []
        unmet: list[float] = []
        viol: list[float] = []
        for seed in range(seeds):
            agents = generate_agents(
                base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family
            )
            agents = with_capability_spread(agents, capability_low)
            agents = with_track_record(agents, random.Random(seed + 40_000))
            agents = with_miscalibration(agents, bias, noise, random.Random(seed + 60_000))
            agents = with_injected_adversarial(
                agents, adversarial_fraction, random.Random(seed + 70_000)
            )
            activation = base.activation_energy if barrier else 0.0
            tasks = generate_tasks(
                base.n_tasks, base.n_domains, random.Random(seed + 10_000), activation, base.family
            )
            res = run_batch(
                agents,
                tasks,
                random.Random(seed + 20_000),
                condition="cta",
                selection_mode="reliability",
                observability_k=base.observability_k,
                gate=gate if gate_on else None,
                gate_enabled=gate_on,
            ).summary()
            q.append(res["mean_quality"])
            unmet.append(res["stall_rate"] + res["infeasible_rate"])
            viol.append(res["integrity_violations"])
        out[name] = {
            "mean_quality": sum(q) / len(q),
            "unmet_rate": sum(unmet) / len(unmet),
            "integrity_violations": sum(viol) / len(viol),
            "quality_values": q,
            "unmet_values": unmet,
            "violation_values": viol,
        }
    return out


def routing_experiment(
    base: CellParams,
    seeds: int,
    observability_levels: tuple[int, ...] = (2, 4, 8, 16),
    n_roles: int = 4,
    heterogeneity: float = 0.5,
) -> list[dict[str, float]]:
    """H10: does the activation barrier route each subtask to a correct specialist?

    A heterogeneous job of one-domain subtasks is run over a fleet of one-domain
    specialists (the domains family, where eligibility is tools and scope only, so
    the Binding Energy alone routes). Because badly matched agents fire only when
    their self-report clears the activation energy, the barrier should keep the
    wrong specialist from ever winning a task. We compare routing accuracy with the
    barrier on (the pre-registered activation energy) and off (activation energy
    zero, every agent fires) across observability levels, since under tight
    observability a task may be seen only by an ill-matched agent, which without
    the barrier would win it. The chance floor is ``1 / n_roles``.
    """
    from cta.routing import routing_accuracy

    out: list[dict[str, float]] = []
    for k in observability_levels:
        on_acc: list[float] = []
        off_acc: list[float] = []
        on_won: list[float] = []
        off_won: list[float] = []
        for seed in range(seeds):
            agents = generate_agents(base.n_agents, n_roles, heterogeneity, random.Random(seed))
            agents = with_track_record(agents, random.Random(seed + 40_000))
            tasks_on = generate_tasks(
                base.n_tasks, n_roles, random.Random(seed + 10_000), base.activation_energy
            )
            tasks_off = generate_tasks(base.n_tasks, n_roles, random.Random(seed + 10_000), 0.0)
            res_on = run_batch(
                agents, tasks_on, random.Random(seed + 20_000), condition="cta",
                selection_mode="reliability", observability_k=k,
            )
            res_off = run_batch(
                agents, tasks_off, random.Random(seed + 20_000), condition="cta",
                selection_mode="reliability", observability_k=k,
            )
            r_on = routing_accuracy(agents, tasks_on, res_on.outcomes)
            r_off = routing_accuracy(agents, tasks_off, res_off.outcomes)
            on_acc.append(r_on["accuracy"])
            off_acc.append(r_off["accuracy"])
            on_won.append(r_on["won"])
            off_won.append(r_off["won"])
        out.append(
            {
                "observability_k": k,
                "chance_floor": 1.0 / n_roles,
                "barrier_on_accuracy": sum(on_acc) / len(on_acc),
                "barrier_off_accuracy": sum(off_acc) / len(off_acc),
                "barrier_on_won": sum(on_won) / len(on_won),
                "barrier_off_won": sum(off_won) / len(off_won),
            }
        )
    return out


def pareto_sweep(
    base: CellParams,
    seeds: int,
    weights: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0),
) -> list[dict[str, float]]:
    """The latency-quality frontier as the bid's latency weight varies (P2.2).

    ``latency_weight`` is the exponent on the latency term of the Binding Energy.
    At zero the bid ignores latency and maximises quality; as it rises the bid
    favours faster agents, trading realised quality for lower mean latency. Each
    point is the mean realised quality and the mean latency of the winning agents
    at one weight, the raw material of a speed-quality product dial.
    """
    out: list[dict[str, float]] = []
    for w in weights:
        q_vals: list[float] = []
        lat_vals: list[float] = []
        for seed in range(seeds):
            agents = generate_agents(
                base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family
            )
            tasks = generate_tasks(
                base.n_tasks,
                base.n_domains,
                random.Random(seed + 10_000),
                base.activation_energy,
                base.family,
            )
            res = run_batch(
                agents, tasks, random.Random(seed + 20_000), condition="cta",
                observability_k=base.observability_k, latency_weight=w,
            )
            by_id = {a.agent_id: a for a in agents}
            won = [o for o in res.outcomes if o.winner is not None]
            if won:
                lat_vals.append(sum(by_id[o.winner].latency for o in won) / len(won))
            q_vals.append(res.summary()["mean_quality"])
        out.append(
            {
                "latency_weight": w,
                "mean_quality": sum(q_vals) / len(q_vals),
                "mean_latency": sum(lat_vals) / len(lat_vals) if lat_vals else 0.0,
            }
        )
    return out


def pareto_front(
    points: list[dict[str, float]],
    quality_key: str = "mean_quality",
    latency_key: str = "mean_latency",
) -> list[dict[str, float]]:
    """The non-dominated points: none has both higher quality and lower latency.

    A point is dominated when another reaches at least its quality at no more than
    its latency, strictly better on one axis. The survivors are the frontier a
    deployer would actually choose between.
    """
    front: list[dict[str, float]] = []
    for p in points:
        dominated = any(
            q is not p
            and q[quality_key] >= p[quality_key]
            and q[latency_key] <= p[latency_key]
            and (q[quality_key] > p[quality_key] or q[latency_key] < p[latency_key])
            for q in points
        )
        if not dominated:
            front.append(p)
    return front


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


def streaming_arrival(
    base: CellParams, seeds: int, arrival_span: int | None = None
) -> dict[str, object]:
    """H5 under non-stationary load (P3.3): does annealing still bound stall when
    tasks arrive over time rather than all at once?

    Uses the same stall-prone scenario as ``annealing_curve`` but staggers the
    tasks' arrival over ``arrival_span`` rounds, and compares the maximum stall,
    the unmet rate, and completion with annealing on and off. A task's stall and
    its barrier annealing are measured from its own arrival, so the mechanism is
    tested under streaming, not just batch, arrival.
    """
    n_agents = max(4, base.n_agents // 4)
    n_tasks = max(4, base.n_tasks // 4)
    span = arrival_span if arrival_span is not None else n_tasks

    def measure(annealing: bool) -> dict[str, float]:
        stalls: list[float] = []
        unmets: list[float] = []
        comps: list[float] = []
        for seed in range(seeds):
            agents, tasks = _stall_scenario(n_agents, n_tasks, random.Random(seed + 90_000))
            res = run_temporal(
                agents,
                tasks,
                random.Random(seed + 80_000),
                TemporalConfig(annealing=annealing, anneal_rate=0.05, arrival_span=span),
            ).summary()
            stalls.append(res["max_stall"])
            unmets.append(res["unmet_rate"])
            comps.append(res["completion_rate"])
        return {
            "max_stall": sum(stalls) / len(stalls),
            "unmet_rate": sum(unmets) / len(unmets),
            "completion_rate": sum(comps) / len(comps),
        }

    return {"arrival_span": span, "anneal_on": measure(True), "anneal_off": measure(False)}


def h2_decomposition(base: CellParams, seeds: int) -> dict[str, float]:
    """Decompose the H2 quality gap into its two causes.

    CTA deploys the ``reliability`` bid, which divides by cost (latency), so it
    trades a little quality for speed. Comparing it against a ``quality`` bid (the
    same competence-weighted score without the latency term) and against the
    full-information optimum separates the two contributions:

    - latency cost: quality gained by dropping cost-awareness (quality minus
      reliability),
    - competence-proxy cost: the residual gap the optimum still holds because it
      knows true capability while CTA sees only the noisy track record (optimum
      minus quality).
    """
    rel: list[float] = []
    qual: list[float] = []
    opt: list[float] = []
    for seed in range(seeds):
        agents = generate_agents(
            base.n_agents, base.n_domains, base.heterogeneity, random.Random(seed), base.family
        )
        tasks = generate_tasks(
            base.n_tasks, base.n_domains, random.Random(seed + 10_000),
            base.activation_energy, base.family,
        )
        rel.append(
            run_batch(
                agents, tasks, random.Random(seed + 20_000), condition="cta",
                observability_k=base.observability_k, selection_mode="reliability",
            ).summary()["mean_quality"]
        )
        qual.append(
            run_batch(
                agents, tasks, random.Random(seed + 20_000), condition="cta",
                observability_k=base.observability_k, selection_mode="quality",
            ).summary()["mean_quality"]
        )
        best = run_central(agents, tasks, random.Random(seed + 20_000), method="best")
        opt.append(best["mean_quality"])
    rel_m = sum(rel) / len(rel)
    qual_m = sum(qual) / len(qual)
    opt_m = sum(opt) / len(opt)
    return {
        "reliability_quality": rel_m,
        "quality_mode_quality": qual_m,
        "optimum_quality": opt_m,
        "latency_cost": qual_m - rel_m,
        "competence_proxy_cost": opt_m - qual_m,
        "total_gap": opt_m - rel_m,
    }


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
