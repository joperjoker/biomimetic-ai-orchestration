"""Tropos: a calibration-robust router for multi-model AI.

Tropos corrects each model's self-reported confidence by an observable track
record, then routes each task to the cheapest model that clears a reliability bar
and escalates the rest. Use it as a library or as an Agent Client Protocol (ACP)
agent. This module re-exports the stable public API; the implementation lives in
the ``cta`` package (Chemotactic Task Allocation), which is the research codebase
the router grew out of.

    from tropos import Fleet, Model, route

The name is from chemotropism: growth toward a chemical signal, the biological
metaphor the framework draws on.
"""

from cta.acp import AcpBroker, serve
from cta.wrappers import (
    Fleet,
    Model,
    RouteDecision,
    TaskContract,
    cost_saving,
    route,
    wrap_task,
)

__all__ = [
    "Fleet",
    "Model",
    "RouteDecision",
    "route",
    "cost_saving",
    "wrap_task",
    "TaskContract",
    "AcpBroker",
    "serve",
]

__version__ = "0.0.1"
