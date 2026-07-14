"""A full step-by-step walkthrough of Tropos: define a fleet, route, learn, re-route.

Everything here is real and deterministic (no model calls). It mirrors the HTML
tour in docs/tropos_tour.html.

    python -m examples.walkthrough
"""

from __future__ import annotations

from tropos import Fleet, Model, route


def step(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    # 1. Define a fleet, cheapest-first, each model on a price tier.
    fleet = Fleet(models=[
        Model("haiku", "economy"),
        Model("sonnet", "standard"),
        Model("opus", "premium"),
    ])
    step("1. Fleet defined: haiku (economy) < sonnet (standard) < opus (premium)")

    # 2. Route a task. You supply each model's confidence bid.
    bids = {"haiku": 0.9, "sonnet": 0.9, "opus": 0.95}
    step("2. Route 'parse' at cold start (no track record yet)")
    d = route("parse", bids, fleet)
    print(f"   bids        : {bids}")
    print(f"   routed to   : {d.model}")
    print(f"   reason      : {d.reason}")

    # 3. Report what actually happened, so Tropos learns.
    step("3. Report real outcomes")
    fleet.record("haiku", "parse", passed=False)
    fleet.record("sonnet", "parse", passed=True)
    fleet.record("sonnet", "parse", passed=True)
    print(f"   haiku  'parse' reliability : {fleet.reliability_of('haiku', 'parse'):.2f}")
    print(f"   sonnet 'parse' reliability : {fleet.reliability_of('sonnet', 'parse'):.2f}")

    # 4. Route the same task again: routing has improved from real outcomes.
    step("4. Route 'parse' again, routing has improved")
    d2 = route("parse", bids, fleet)
    print(f"   routed to   : {d2.model}")
    print(f"   reason      : {d2.reason}")

    print("\nSame bids, better routing: Tropos dropped haiku on 'parse' after seeing it")
    print("fail, and moved to the cheaper reliable model. It learns from real outcomes.")


if __name__ == "__main__":
    main()
