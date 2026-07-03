"""Tests for the Stage 2 pilot scaffold (mock client, no model calls)."""

import random

import pytest

from cta.generators import generate_agents, generate_tasks
from cta.pilot import ClaudeAgentClient, MockClient, run_pilot
from cta.scoring import Agent, Task


def test_mock_pilot_runs_end_to_end():
    agents = generate_agents(20, 4, 0.8, random.Random(1))
    tasks = generate_tasks(15, 4, random.Random(2), 0.2)
    result = run_pilot(agents, tasks, MockClient(seed=3))
    s = result.summary()
    assert s["tasks"] == 15
    assert 0.0 <= s["completion_rate"] <= 1.0
    # Winners' outcomes feed the same calibration measures as the simulation.
    assert set(("overconfidence_gap", "winner_brier", "winner_ece")) <= set(s)
    # The track record accumulates online: some agent has more attempts than it
    # started with, because it won and executed at least one task.
    started = sum(a.attempts for a in agents)
    ended = sum(n for _, n in result.track_record.values())
    assert ended > started


def test_mock_pilot_is_deterministic():
    agents = generate_agents(12, 4, 0.8, random.Random(5))
    tasks = generate_tasks(10, 4, random.Random(6), 0.2)
    a = run_pilot(agents, tasks, MockClient(seed=7)).summary()
    b = run_pilot(agents, tasks, MockClient(seed=7)).summary()
    assert a == b


def test_gate_deflects_out_of_scope_in_pilot():
    # A single adversarial agent that always acts out of scope is deflected by the
    # gate, so no integrity violation is recorded.
    agent = Agent(
        agent_id="adv",
        skills=frozenset({"skill_0"}),
        tools=frozenset({"edit", "test"}),
        permitted_scope=frozenset({"src/**", "tests/**"}),
        capability_vector=(1.0, 0.0, 0.0, 0.0),
        capability=0.9,
        successes=18,
        attempts=20,
        out_of_scope_prob=1.0,
    )
    task = Task(
        task_id="t0",
        required_skills=frozenset({"skill_0"}),
        required_tools=frozenset({"edit", "test"}),
        scope=frozenset({"src/**"}),
        requirement_vector=(1.0, 0.0, 0.0, 0.0),
        activation_energy=0.2,
    )
    on = run_pilot([agent], [task], MockClient(seed=1), gate_enabled=True).summary()
    off = run_pilot([agent], [task], MockClient(seed=1), gate_enabled=False).summary()
    assert on["integrity_violations"] == 0
    assert off["integrity_violations"] == 1


def test_real_client_is_inert():
    # The live client must not make a call until implemented and approved.
    client = ClaudeAgentClient()
    agent = generate_agents(1, 4, 0.8, random.Random(1))[0]
    task = generate_tasks(1, 4, random.Random(2), 0.2)[0]
    with pytest.raises(NotImplementedError):
        client.assess(agent, task)
    with pytest.raises(NotImplementedError):
        client.perform(agent, task)
