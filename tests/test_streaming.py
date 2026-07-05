"""P3.3: annealing bounds stall under streaming (non-stationary) task arrival."""

import random

from cta.generators import generate_agents, generate_tasks
from cta.harness import CellParams, streaming_arrival
from cta.temporal import TemporalConfig, run_temporal


def test_batch_arrival_is_unchanged_when_span_zero():
    # arrival_span 0 must preserve the original batch behaviour exactly.
    agents = generate_agents(20, 3, 0.8, random.Random(1))
    tasks = generate_tasks(15, 3, random.Random(2), 0.3)
    a = run_temporal(agents, tasks, random.Random(3), TemporalConfig(arrival_span=0)).summary()
    b = run_temporal(agents, tasks, random.Random(3), TemporalConfig()).summary()
    assert a == b


def test_streaming_arrival_advertises_over_time():
    # With a span, tasks are advertised at staggered rounds, not all at zero.
    agents = generate_agents(20, 3, 0.8, random.Random(1))
    tasks = generate_tasks(20, 3, random.Random(2), 0.2)
    res = run_temporal(agents, tasks, random.Random(3), TemporalConfig(arrival_span=20))
    advertised = {o.advertised_at for o in res.outcomes}
    assert len(advertised) > 1  # more than one distinct arrival round
    assert max(advertised) > 0


def test_annealing_bounds_stall_under_streaming():
    base = CellParams(n_agents=40, n_tasks=48)
    r = streaming_arrival(base, seeds=8)
    on, off = r["anneal_on"], r["anneal_off"]
    # Under streaming arrival, annealing still resolves feasible tasks with a
    # bounded stall, while without it they stall to the horizon and go unmet.
    assert on["unmet_rate"] < 0.1
    assert off["unmet_rate"] > 0.5
    assert on["max_stall"] < off["max_stall"]
