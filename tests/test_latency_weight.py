"""The latency-weight exponent tunes how hard the bid favours faster agents."""

import random

from cta.engine import _bid, run_batch
from cta.generators import generate_agents, generate_tasks
from cta.scoring import Agent


def _agent(latency: float) -> Agent:
    return Agent(agent_id=f"a{latency}", latency=latency, successes=10, attempts=20, capability=1.0)


def test_latency_weight_zero_ignores_latency():
    slow, fast = _agent(2.0), _agent(0.5)
    # With weight 0 the latency term is L**0 = 1, so equal self-reports tie.
    assert _bid("reliability", 0.8, 0.8, slow, 0.0) == _bid("reliability", 0.8, 0.8, fast, 0.0)


def test_higher_weight_favours_faster_agents_more():
    slow, fast = _agent(2.0), _agent(0.5)
    gap1 = _bid("reliability", 0.8, 0.8, fast, 1.0) - _bid("reliability", 0.8, 0.8, slow, 1.0)
    gap2 = _bid("reliability", 0.8, 0.8, fast, 2.0) - _bid("reliability", 0.8, 0.8, slow, 2.0)
    assert gap1 > 0.0
    assert gap2 > gap1  # a larger exponent widens the advantage of the fast agent


def test_run_batch_accepts_latency_weight_and_is_deterministic():
    agents = generate_agents(20, 3, 0.8, random.Random(3))
    tasks = generate_tasks(15, 3, random.Random(4))
    r1 = run_batch(agents, tasks, random.Random(5), condition="cta", latency_weight=0.0).summary()
    r2 = run_batch(agents, tasks, random.Random(5), condition="cta", latency_weight=0.0).summary()
    assert r1 == r2
