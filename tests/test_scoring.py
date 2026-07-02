"""Known-value and behaviour tests for the CTA scoring model (E1 to E11)."""

import math

from cta.scoring import (
    Agent,
    GateConfig,
    Task,
    activation_drive,
    binding_energy,
    compatibility,
    cosine,
    effective_capability,
    eligible,
    gate_admits,
    p_fire,
    reliability,
    select_winner,
)


def _agent(**kw):
    return Agent(agent_id=kw.pop("agent_id", "a"), **kw)


def test_cosine_known_values():
    assert cosine((1.0, 0.0), (1.0, 0.0)) == 1.0
    assert cosine((1.0, 0.0), (0.0, 1.0)) == 0.0
    assert cosine((), (1.0,)) == 0.0
    assert math.isclose(cosine((1.0, 1.0), (1.0, 0.0)), 1 / math.sqrt(2), rel_tol=1e-9)


def test_eligibility_hard_gate():
    task = Task("t", required_tools=frozenset({"pytest"}), scope=frozenset({"src/**"}))
    ok = _agent(tools=frozenset({"pytest", "ruff"}), permitted_scope=frozenset({"src/**"}))
    no_tool = _agent(tools=frozenset({"ruff"}), permitted_scope=frozenset({"src/**"}))
    no_scope = _agent(tools=frozenset({"pytest"}), permitted_scope=frozenset({"docs/**"}))
    assert eligible(ok, task) is True
    assert eligible(no_tool, task) is False
    assert eligible(no_scope, task) is False


def test_compatibility_perfect_and_zero():
    task = Task(
        "t",
        required_skills=frozenset({"python"}),
        scope=frozenset({"src/**"}),
        requirement_vector=(1.0, 0.0),
    )
    perfect = _agent(
        skills=frozenset({"python"}),
        permitted_scope=frozenset({"src/**"}),
        capability_vector=(1.0, 0.0),
    )
    c = compatibility(perfect, task)
    assert 0.95 <= c <= 1.0
    # Missing the only required skill craters the geometric mean well below a
    # perfect match (the zero sub-score applies a strong multiplicative penalty).
    no_skill = _agent(
        skills=frozenset(),
        permitted_scope=frozenset({"src/**"}),
        capability_vector=(1.0, 0.0),
    )
    assert compatibility(no_skill, task) < 0.25
    assert compatibility(no_skill, task) < 0.4 * c


def test_compatibility_is_deterministic():
    task = Task("t", requirement_vector=(0.3, 0.7), required_skills=frozenset({"go"}))
    a = _agent(skills=frozenset({"go"}), capability_vector=(0.3, 0.7))
    assert compatibility(a, task) == compatibility(a, task)


def test_reliability_laplace():
    assert reliability(_agent(successes=0, attempts=0)) == 0.5
    assert math.isclose(reliability(_agent(successes=9, attempts=10)), 10 / 12)
    assert reliability(_agent(successes=0, attempts=10)) < 0.1


def test_effective_capability_couples_reliability():
    a = _agent(capability=1.0, successes=0, attempts=0)
    assert math.isclose(effective_capability(a), 0.5)


def test_binding_energy_latency_floor():
    task = Task("t", requirement_vector=(1.0,), required_skills=frozenset())
    fast = _agent(capability_vector=(1.0,), capability=1.0, latency=0.0)
    # Latency is floored at EPS, so B is finite (no division error), not unbounded.
    expected = compatibility(fast, task) * effective_capability(fast) / 0.01
    assert binding_energy(fast, task) == expected


def test_activation_and_firing_threshold():
    task = Task("t", requirement_vector=(1.0,), activation_energy=0.2)
    a = _agent(capability_vector=(1.0,))
    assert activation_drive(a, task) >= 0.0
    assert p_fire(a, task, temperature=0.0) == 1.0
    # An agent well below the barrier does not fire deterministically.
    weak = _agent(capability_vector=(0.0, 1.0))
    weak_task = Task("t", requirement_vector=(1.0, 0.0), activation_energy=0.5)
    assert p_fire(weak, weak_task, temperature=0.0) == 0.0
    # With temperature, a sub-barrier match fires with probability in (0, 1).
    p = p_fire(weak, weak_task, temperature=0.2)
    assert 0.0 < p < 1.0


def test_select_winner_prefers_higher_binding_energy():
    task = Task(
        "t",
        required_tools=frozenset({"pytest"}),
        scope=frozenset({"src/**"}),
        requirement_vector=(1.0, 0.0),
        activation_energy=0.2,
    )
    base = dict(
        tools=frozenset({"pytest"}),
        permitted_scope=frozenset({"src/**"}),
        capability_vector=(1.0, 0.0),
        capability=1.0,
        successes=20,
        attempts=20,
    )
    cheap = Agent(agent_id="cheap", latency=0.5, **base)
    dear = Agent(agent_id="dear", latency=2.0, **base)
    winner = select_winner([dear, cheap], task)
    assert winner is not None and winner.agent_id == "cheap"


def test_select_winner_none_when_all_below_barrier():
    task = Task("t", requirement_vector=(1.0, 0.0), activation_energy=0.9)
    a = Agent(agent_id="a", capability_vector=(0.0, 1.0))
    assert select_winner([a], task) is None


def test_gate_admits_on_reliability_and_scope():
    task = Task("t")
    reliable = _agent(successes=20, attempts=20)
    degraded = _agent(successes=1, attempts=20)
    assert gate_admits(reliable, task, in_scope=True) is True
    assert gate_admits(reliable, task, in_scope=False) is False
    assert gate_admits(degraded, task, in_scope=True) is False
    # A stricter threshold deflects even a strong agent (R = 21/22 is below 0.99).
    assert gate_admits(reliable, task, in_scope=True, config=GateConfig(0.99)) is False
