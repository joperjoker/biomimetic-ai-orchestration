"""The routing-correctness metric identifies the right specialist."""

import random

from cta.engine import TaskOutcome, run_batch
from cta.generators import generate_agents, generate_tasks
from cta.routing import agent_home, dominant_index, required_domain, routing_accuracy


def test_dominant_index_and_labels():
    assert dominant_index([0.1, 0.8, 0.1]) == 1
    assert dominant_index([0.5, 0.5, 0.0]) == 0  # ties to the lowest index
    # At full heterogeneity, agents are pure one-hot specialists and tasks one-hot.
    agents = generate_agents(6, 3, 1.0, random.Random(1))
    tasks = generate_tasks(6, 3, random.Random(2))
    assert all(0 <= agent_home(a) < 3 for a in agents)
    assert all(0 <= required_domain(t) < 3 for t in tasks)


def test_routing_accuracy_counts_only_won_tasks():
    agents = [type("A", (), {"agent_id": "a", "capability_vector": (1.0, 0.0)})()]
    tasks = [
        type("T", (), {"task_id": "t0", "requirement_vector": (1.0, 0.0)})(),
        type("T", (), {"task_id": "t1", "requirement_vector": (0.0, 1.0)})(),
    ]
    outcomes = [
        TaskOutcome(task_id="t0", status="COMPLETED", winner="a", quality=0.9, fired=1),
        TaskOutcome(task_id="t1", status="COMPLETED", winner="a", quality=0.9, fired=1),
        TaskOutcome(task_id="t2", status="STALLED", winner=None, quality=None, fired=0),
    ]
    r = routing_accuracy(agents, tasks, outcomes)
    # Agent a (domain 0) correctly wins t0 (domain 0), wrongly wins t1 (domain 1);
    # the unwon t2 is ignored.
    assert r["won"] == 2 and r["correct"] == 1
    assert r["accuracy"] == 0.5


def test_calibrated_specialists_route_well():
    # With honest specialists, the binding energy sends most tasks to the right
    # specialist, so routing accuracy is high.
    agents = generate_agents(40, 4, 1.0, random.Random(7))
    tasks = generate_tasks(32, 4, random.Random(8))
    res = run_batch(agents, tasks, random.Random(9), condition="cta")
    acc = routing_accuracy(agents, tasks, res.outcomes)["accuracy"]
    assert acc > 0.9
