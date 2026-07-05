"""Guards for the wrapper product API (`cta.wrappers`)."""

from cta.wrappers import Fleet, Model, cost_saving, route, wrap_task


def test_task_wrapper_envelope_contains_contract():
    c = wrap_task(
        "f", "def f(x): ...", "does a thing",
        acceptance=["handles empty"], self_check=["f(0) -> 0"],
    )
    env = c.envelope()
    assert "def f(x)" in env
    assert "handles empty" in env
    assert "Self-check" in env


def test_fleet_orders_cheapest_first_and_prices():
    fleet = Fleet(models=[Model("opus", "premium"), Model("haiku", "economy")])
    assert fleet.cheapest().name == "haiku"
    assert fleet.most_capable().name == "opus"
    assert fleet.cheapest().blended_rate() < fleet.most_capable().blended_rate()


def test_router_routes_cheap_when_reliable_and_escalates_when_not():
    fleet = Fleet(models=[Model("haiku", "economy"), Model("sonnet", "standard")])
    # Reliable cheap model -> cheapest clears the barrier.
    fleet.reliability = {"haiku": {"easy": 0.9}, "sonnet": {"easy": 0.95}}
    assert route("easy", {"haiku": 0.9, "sonnet": 0.9}, fleet).model == "haiku"
    # Unreliable cheap model on this task -> escalate to the stronger one.
    fleet.reliability = {"haiku": {"hard": 0.35}, "sonnet": {"hard": 0.9}}
    d = route("hard", {"haiku": 0.9, "sonnet": 0.9}, fleet)
    assert d.model == "sonnet"
    assert "haiku" not in d.eligible


def test_record_updates_track_record_toward_outcome():
    fleet = Fleet(models=[Model("haiku", "economy")])
    before = fleet.reliability_of("haiku", "t")
    for _ in range(20):
        fleet.record("haiku", "t", passed=False)
    assert fleet.reliability_of("haiku", "t") < before


def test_cost_saving_beats_always_frontier():
    fleet = Fleet(models=[Model("haiku", "economy"), Model("opus", "premium")])
    routed = [("haiku", 4000.0), ("haiku", 4000.0), ("opus", 4000.0)]
    s = cost_saving(routed, fleet, 4000.0)
    assert s["saving_multiple"] > 1.0
    assert s["routed_usd"] < s["always_top_usd"]
