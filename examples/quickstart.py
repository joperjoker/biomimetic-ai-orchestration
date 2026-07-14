"""60-second quickstart: route a fleet with the calibration-robust router.

The router corrects each model's self-reported confidence by an observable track
record, then sends each task to the cheapest model that clears a reliability bar
and escalates the rest. This runs offline and deterministically, no model calls.

    python -m examples.quickstart
"""

from __future__ import annotations

from cta.wrappers import Fleet, Model, route

# A cheap-to-expensive fleet at representative price tiers.
fleet = Fleet(models=[
    Model("haiku", "economy"),
    Model("sonnet", "standard"),
    Model("opus", "premium"),
])

# What the router has learned so far (its track record): the cheap model is
# reliable on "format" but confidently wrong on "parse"; the stronger models are
# reliable on both. In a real deployment this table fills in from actual outcomes.
fleet.reliability = {
    "haiku": {"format": 0.95, "parse": 0.30},
    "sonnet": {"format": 0.97, "parse": 0.95},
    "opus": {"format": 0.99, "parse": 0.98},
}


def main() -> None:
    print("task    -> routed model   (why)")
    for task in ("format", "parse"):
        # Every model bids the same high self-report; the correction is what
        # separates them.
        bids = {"haiku": 0.9, "sonnet": 0.9, "opus": 0.95}
        d = route(task, bids, fleet)
        print(f"{task:7} -> {d.model:7}       {d.reason}")
    print(
        "\nThe cheap model handles 'format'; 'parse' escalates to the cheapest model\n"
        "that is actually reliable on it. Same self-reports, different routing, because\n"
        "the track record corrects them."
    )


if __name__ == "__main__":
    main()
