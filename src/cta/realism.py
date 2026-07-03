"""A realistic mixed fleet, parameterised from measured LLM calibration.

The simulation's synthetic miscalibration model is replaced here by agent
archetypes whose stated-versus-realised gaps span the range reported for current
coding models. MarketBench (Fradkin and Krishnan, 2026, arXiv:2604.23897), on
SWE-bench Lite over six frontier models, finds realised pass rates clustered
around 0.75 to 0.81 while stated success probabilities range from 0.61 to 0.93:
a Gemini-class model is sharply overconfident, GPT-mini-class models are
underconfident, and the Claude models are well calibrated. The three profiles
below span that spread.

The self-report here is an estimate of success (fit times competence), as in the
auction setting MarketBench studies, not of fit alone, so a well-calibrated
archetype has a small overconfidence gap and the reliability diagram of the fleet
is directly comparable to the measured calibration curves. The fleet runs through
the same pilot pipeline as the live path, so no part of the framework is special-
cased for realism.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace

from cta.engine import _brier_ece, reliability_bins
from cta.generators import generate_agents, generate_tasks, with_injected_adversarial
from cta.pilot import PilotClient, run_pilot
from cta.quality import realised_quality
from cta.scoring import Agent, Task, compatibility


def _clip01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


@dataclass(frozen=True)
class Profile:
    """A calibration archetype, grounded in the MarketBench spread."""

    name: str
    capability_mean: float
    capability_sd: float
    calibration_bias: float  # stated minus realised success, from the reported range
    calibration_noise: float


PROFILES: tuple[Profile, ...] = (
    Profile("overconfident", 0.78, 0.06, 0.15, 0.06),  # Gemini-class
    Profile("calibrated", 0.80, 0.05, 0.00, 0.04),  # Claude-class
    Profile("underconfident", 0.78, 0.06, -0.16, 0.06),  # GPT-mini-class
)
_BY_NAME = {p.name: p for p in PROFILES}


def _assign(n: int, mix: dict[str, float] | None, rng: random.Random) -> list[Profile]:
    if mix is None:
        weights = [1.0 for _ in PROFILES]
        names = [p.name for p in PROFILES]
    else:
        names = list(mix.keys())
        weights = [max(0.0, mix[k]) for k in names]
    total = sum(weights) or 1.0
    cum: list[tuple[float, str]] = []
    acc = 0.0
    for name, w in zip(names, weights, strict=False):
        acc += w / total
        cum.append((acc, name))
    out: list[Profile] = []
    for _ in range(n):
        u = rng.random()
        chosen = cum[-1][1]
        for threshold, name in cum:
            if u <= threshold:
                chosen = name
                break
        out.append(_BY_NAME[chosen])
    return out


def generate_fleet(
    n: int,
    n_domains: int,
    heterogeneity: float,
    rng: random.Random,
    mix: dict[str, float] | None = None,
) -> list[Agent]:
    """A mixed fleet: domains-structured agents with archetype capability and bias.

    Reuses the domains generator for the task-fit structure (skills, vectors, tools)
    and overrides each agent's capability, calibration, and track record from its
    assigned archetype, so the fleet resembles a real mix of coding models.
    """
    base = generate_agents(n, n_domains, heterogeneity, rng)
    profiles = _assign(n, mix, rng)
    out: list[Agent] = []
    for a, prof in zip(base, profiles, strict=False):
        cap = _clip01(rng.gauss(prof.capability_mean, prof.capability_sd))
        attempts = 20
        successes = sum(1 for _ in range(attempts) if rng.random() < cap)
        out.append(
            replace(
                a,
                role=prof.name,
                capability=cap,
                calibration_bias=prof.calibration_bias,
                calibration_noise=prof.calibration_noise,
                successes=successes,
                attempts=attempts,
            )
        )
    return out


@dataclass
class FleetClient:
    """A pilot client whose self-report is a success estimate with archetype bias."""

    seed: int = 0

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def assess(self, agent: Agent, task: Task) -> float:
        true_success = compatibility(agent, task) * _clip01(agent.capability)
        noise = (
            0.0
            if agent.calibration_noise <= 0
            else agent.calibration_noise * self._rng.gauss(0.0, 1.0)
        )
        return _clip01(true_success + agent.calibration_bias + noise)

    def perform(self, agent: Agent, task: Task) -> tuple[float, bool]:
        quality = realised_quality(compatibility(agent, task), agent.capability, self._rng)
        in_scope = self._rng.random() >= agent.out_of_scope_prob
        return quality, in_scope


def _executed(outcomes: list) -> tuple[list[float], list[float]]:
    done = [o for o in outcomes if o.status in ("COMPLETED", "FAILED")]
    preds = [float(o.self_report) for o in done]
    succ = [1.0 if o.status == "COMPLETED" else 0.0 for o in done]
    return preds, succ


def fleet_experiment(
    n_agents: int = 60,
    n_tasks: int = 48,
    seeds: int = 20,
    mix: dict[str, float] | None = None,
) -> dict[str, object]:
    """Run the realistic fleet under raw and reliability selection.

    Returns the completion recovery, the calibration error under each selection,
    and the reliability-diagram bins (mean prediction versus realised success)
    pooled across seeds, so the fleet's real-archetype miscalibration is both
    measured and plottable.
    """
    rel: list[float] = []
    raw: list[float] = []
    preds_raw: list[float] = []
    succ_raw: list[float] = []
    preds_rel: list[float] = []
    succ_rel: list[float] = []
    client: PilotClient
    for seed in range(seeds):
        agents = generate_fleet(n_agents, 4, 0.8, random.Random(seed), mix)
        tasks = generate_tasks(n_tasks, 4, random.Random(seed + 10_000), 0.2)
        client = FleetClient(seed + 80_000)
        r_raw = run_pilot(agents, tasks, client, selection="raw")
        client = FleetClient(seed + 80_000)
        r_rel = run_pilot(agents, tasks, client, selection="reliability")
        raw.append(r_raw.summary()["completion_rate"])
        rel.append(r_rel.summary()["completion_rate"])
        pr, sr = _executed(r_raw.outcomes)
        preds_raw += pr
        succ_raw += sr
        pe, se = _executed(r_rel.outcomes)
        preds_rel += pe
        succ_rel += se
    raw_m = sum(raw) / len(raw)
    rel_m = sum(rel) / len(rel)
    return {
        "raw_completion": raw_m,
        "reliability_completion": rel_m,
        "recovery": rel_m - raw_m,
        "brier_raw": _brier_ece(preds_raw, succ_raw)[0],
        "brier_reliability": _brier_ece(preds_rel, succ_rel)[0],
        "bins_raw": reliability_bins(preds_raw, succ_raw),
        "bins_reliability": reliability_bins(preds_rel, succ_rel),
    }


def fleet_mix_sweep(
    seeds: int = 20,
    fractions: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
    n_agents: int = 60,
    n_tasks: int = 48,
) -> list[dict[str, float]]:
    """Recovery as the fleet's fraction of overconfident agents rises.

    The rest of the fleet is split evenly between calibrated and underconfident.
    """
    out: list[dict[str, float]] = []
    for f in fractions:
        rest = (1.0 - f) / 2.0
        mix = {"overconfident": f, "calibrated": rest, "underconfident": rest}
        raw: list[float] = []
        rel: list[float] = []
        for seed in range(seeds):
            agents = generate_fleet(n_agents, 4, 0.8, random.Random(seed), mix)
            tasks = generate_tasks(n_tasks, 4, random.Random(seed + 10_000), 0.2)
            raw.append(
                run_pilot(agents, tasks, FleetClient(seed + 80_000), selection="raw")
                .summary()["completion_rate"]
            )
            rel.append(
                run_pilot(agents, tasks, FleetClient(seed + 80_000), selection="reliability")
                .summary()["completion_rate"]
            )
        raw_m = sum(raw) / len(raw)
        rel_m = sum(rel) / len(rel)
        out.append(
            {
                "overconfident_fraction": f,
                "raw_completion": raw_m,
                "reliability_completion": rel_m,
                "recovery": rel_m - raw_m,
            }
        )
    return out


def adversarial_fleet_safety(
    seeds: int = 20, adversarial_fraction: float = 0.3, gate_recall: float = 0.9
) -> dict[str, float]:
    """Integrity violations on the realistic fleet, with the gate on and off."""
    from cta.scoring import GateConfig

    on: list[float] = []
    off: list[float] = []
    gate = GateConfig(scope_recall=gate_recall)
    for seed in range(seeds):
        agents = generate_fleet(60, 4, 0.8, random.Random(seed))
        agents = with_injected_adversarial(
            agents, adversarial_fraction, random.Random(seed + 70_000)
        )
        tasks = generate_tasks(48, 4, random.Random(seed + 10_000), 0.2)
        on.append(
            run_pilot(
                agents, tasks, FleetClient(seed + 80_000), gate=gate, gate_enabled=True,
                rng=random.Random(seed + 90_000),
            ).summary()["integrity_violations"]
        )
        off.append(
            run_pilot(agents, tasks, FleetClient(seed + 80_000), gate_enabled=False)
            .summary()["integrity_violations"]
        )
    on_m = sum(on) / len(on)
    off_m = sum(off) / len(off)
    return {
        "gate_on_violations": on_m,
        "gate_off_violations": off_m,
        "reduction": 1.0 - on_m / off_m if off_m > 0 else 0.0,
    }
