"""Tests for the Auto-Researcher loop and its guardrails."""

import random

from cta.autoresearch import run_loop
from cta.autoresearch.loop import evaluate_point
from cta.autoresearch.search_space import BOUNDS, SearchPoint, propose
from cta.harness import CellParams


def test_propose_stays_within_bounds():
    rng = random.Random(0)
    point = SearchPoint(0.2, 0.0)
    for _ in range(200):
        point = propose(point, rng)
        ea_lo, ea_hi = BOUNDS["activation_energy"]
        t_lo, t_hi = BOUNDS["temperature"]
        assert ea_lo <= point.activation_energy <= ea_hi
        assert t_lo <= point.temperature <= t_hi


def test_evaluate_point_ranges():
    base = CellParams(n_agents=30, n_tasks=24, n_domains=4, heterogeneity=0.8)
    quality, unmet = evaluate_point(SearchPoint(0.2, 0.0), base, seeds=3)
    assert 0.0 <= quality <= 1.0
    assert 0.0 <= unmet <= 1.0


def test_loop_is_deterministic_and_respects_guardrail():
    base = CellParams(n_agents=30, n_tasks=24, n_domains=4, heterogeneity=0.8)
    r1 = run_loop(base, seeds=3, budget=6, seed=1)
    r2 = run_loop(base, seeds=3, budget=6, seed=1)
    assert r1.best_objective == r2.best_objective
    assert len(r1.ledger) == 6
    # The loop never keeps a change that breaches the guardrail.
    for d in r1.ledger:
        if d.kept:
            assert d.guardrail_ok is True
    # The best objective never decreases below the starting evaluation.
    assert r1.best_objective >= r1.ledger[0].objective_before - 1e-9
