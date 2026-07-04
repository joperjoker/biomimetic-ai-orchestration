"""Routing correctness for the heterogeneous specialist experiment (H10, P2.7).

In the domains family, eligibility is by tools and scope alone, and every agent
holds both, so nothing routes a task except the Binding Energy. Each task in this
family requires one domain (a one-hot requirement vector) and each specialist
agent is peaked on one domain (a one-hot capability vector). A task is routed
correctly when the agent that wins it is a specialist in the task's required
domain. This module computes that correctness from the engine's outcomes, so the
question "does the binding energy route each subtask to its correct specialist"
becomes a number.
"""

from __future__ import annotations

from collections.abc import Sequence

from cta.engine import TaskOutcome
from cta.scoring import Agent, Task


def dominant_index(vector: Sequence[float]) -> int:
    """Index of the largest component (ties resolved to the lowest index)."""
    best_i = -1
    best_v = float("-inf")
    for i, v in enumerate(vector):
        if v > best_v:
            best_v = v
            best_i = i
    return best_i


def required_domain(task: Task) -> int:
    """The domain a task requires: the peak of its one-hot requirement vector."""
    return dominant_index(task.requirement_vector)


def agent_home(agent: Agent) -> int:
    """The domain an agent specialises in: the peak of its capability vector."""
    return dominant_index(agent.capability_vector)


def routing_accuracy(
    agents: Sequence[Agent], tasks: Sequence[Task], outcomes: Sequence[TaskOutcome]
) -> dict[str, float]:
    """Fraction of won tasks whose winner specialises in the task's domain.

    Only tasks that were actually won (a winner was selected) count towards the
    denominator, so this measures routing quality among the allocations made, not
    coverage. Returns the accuracy, the number of won tasks, and the number routed
    to the correct specialist.
    """
    home = {a.agent_id: agent_home(a) for a in agents}
    need = {t.task_id: required_domain(t) for t in tasks}
    won = 0
    correct = 0
    for o in outcomes:
        if o.winner is None:
            continue
        won += 1
        if home.get(o.winner) == need.get(o.task_id):
            correct += 1
    return {
        "won": won,
        "correct": correct,
        "accuracy": correct / won if won else 0.0,
    }
