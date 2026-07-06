"""Guard for the reputation-gaming (sandbagging) adversary experiment."""

from cta.harness import CellParams, sandbagging_adversary


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
