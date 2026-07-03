"""Tests for the round-based temporal engine and the annealing behaviour (E14)."""

import random

from cta.generators import generate_agents, generate_tasks
from cta.harness import CellParams, annealing_curve, temporal_metrics
from cta.scoring import Agent, Task
from cta.temporal import TemporalConfig, run_temporal


def _generalist_pool(n: int, rng: random.Random) -> list[Agent]:
    # Uniform capability vector, so cosine to any single-domain task is 0.5 and
    # compatibility is about 0.707, below a 0.85 barrier.
    uniform = (0.25, 0.25, 0.25, 0.25)
    skills = frozenset(f"skill_{d}" for d in range(4))
    return [
        Agent(
            agent_id=f"gen_{i}",
            skills=skills,
            tools=frozenset({"edit", "test"}),
            permitted_scope=frozenset({"src/**", "tests/**"}),
            capability_vector=uniform,
            capability=0.7,
            successes=8,
            attempts=10,
            latency=0.5 + rng.random(),
        )
        for i in range(n)
    ]


def _stall_tasks(n: int) -> list[Task]:
    return [
        Task(
            task_id=f"stall_{k}",
            required_skills=frozenset({f"skill_{k % 4}"}),
            required_tools=frozenset({"edit", "test"}),
            scope=frozenset({"src/**"}),
            requirement_vector=tuple(1.0 if d == k % 4 else 0.0 for d in range(4)),
            activation_energy=0.85,
        )
        for k in range(n)
    ]


def test_temporal_is_deterministic():
    agents = generate_agents(20, 4, 0.8, random.Random(1))
    tasks = generate_tasks(15, 4, random.Random(2), 0.2)
    a = run_temporal(agents, tasks, random.Random(3)).summary()
    b = run_temporal(agents, tasks, random.Random(3)).summary()
    assert a == b
    assert a["tasks"] == 15


def test_annealing_resolves_feasible_stalls():
    agents = _generalist_pool(12, random.Random(1))
    tasks = _stall_tasks(8)
    on = run_temporal(agents, tasks, random.Random(3), TemporalConfig(annealing=True)).summary()
    off = run_temporal(agents, tasks, random.Random(3), TemporalConfig(annealing=False)).summary()
    # Without annealing the feasible tasks are never claimed and stay unmet, with
    # an unbounded stall; with annealing they resolve at a bounded stall.
    assert off["unmet_rate"] == 1.0
    assert on["unmet_rate"] == 0.0
    assert on["max_stall"] < off["max_stall"]


def test_annealing_curve_bounds_stall():
    base = CellParams(n_agents=40, n_tasks=32, n_domains=4, heterogeneity=0.8)
    curve = annealing_curve(base, seeds=2, rates=(0.0, 0.1))
    assert curve[0]["max_stall"] > curve[-1]["max_stall"]
    assert curve[0]["unmet_rate"] > curve[-1]["unmet_rate"]


def test_temporal_metrics_shapes():
    base = CellParams(n_agents=40, n_tasks=32, n_domains=4, heterogeneity=0.8)
    tm = temporal_metrics(base, seeds=2)
    assert set(tm) == {"mean_latency", "throughput", "max_stall", "completion_rate"}
    assert all(len(v) == 2 for v in tm.values())
