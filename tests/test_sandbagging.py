"""Guards for the reputation-gaming adversary and the exposure-cap defence."""

import random

from cta.engine import run_batch
from cta.generators import generate_agents, generate_tasks
from cta.harness import CellParams, exposure_cap_defense, sandbagging_adversary


def test_sandbagging_exploits_reputation_and_window_shortens_it():
    r = sandbagging_adversary(CellParams(), seeds=6)
    rounds, honest = r["rounds"], r["honest_rounds"]
    assert len(r["cumulative_share"]) == rounds
    assert all(0.0 <= s <= 1.0 for s in r["cumulative_share"] + r["windowed_share"])
    # Honest phase does little damage; the defection is what causes failed wins.
    honest_damage = sum(r["cumulative_fail"][:honest])
    assert r["cumulative_damage"] > honest_damage
    # The adversary genuinely exploits its reputation after defecting.
    assert r["cumulative_damage"] > 0
    # A recency-weighted window does not increase, and here reduces, the damage.
    assert r["windowed_damage"] <= r["cumulative_damage"]


def test_exposure_cap_limits_per_agent_wins():
    agents = generate_agents(60, 4, 0.6, random.Random(0))
    tasks = generate_tasks(60, 4, random.Random(1), 0.2)
    res = run_batch(agents, tasks, random.Random(2), condition="cta", exposure_cap=1)
    wins: dict[str, int] = {}
    for o in res.outcomes:
        if o.winner is not None:
            wins[o.winner] = wins.get(o.winner, 0) + 1
    assert wins and max(wins.values()) <= 1


def test_exposure_cap_bounds_first_defection_blast_radius():
    r = exposure_cap_defense(CellParams(), seeds=6)
    dmg = r["first_defect_damage"]
    # A cap of one bounds each adversary to at most one win, so the failed wins
    # cannot exceed the adversary count, and it is below the unthrottled baseline.
    assert dmg["1"] <= r["n_adversaries"]
    assert dmg["1"] <= dmg["None"]
