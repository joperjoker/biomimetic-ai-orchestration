"""Tests for the realistic fleet grounded in measured LLM calibration."""

import random
import statistics

from cta.engine import reliability_bins
from cta.generators import generate_agents, generate_tasks
from cta.realism import (
    PROFILES,
    FleetClient,
    fleet_experiment,
    fleet_mix_sweep,
    generate_fleet,
    with_fitted_miscalibration,
)


def test_fitted_miscalibration_draws_from_measured_profiles():
    agents = generate_agents(50, 4, 0.8, random.Random(2))
    fitted = with_fitted_miscalibration(agents, random.Random(9))
    biases = {p.calibration_bias for p in PROFILES}
    # Every agent's calibration bias is one of the measured archetype values.
    assert all(a.calibration_bias in biases for a in fitted)
    # The population spans more than one archetype under the default equal mix.
    assert len({a.calibration_bias for a in fitted}) >= 2
    # Deterministic under the seed; only calibration is overridden.
    again = with_fitted_miscalibration(agents, random.Random(9))
    assert [a.calibration_bias for a in fitted] == [a.calibration_bias for a in again]
    assert [a.capability for a in fitted] == [a.capability for a in agents]


def test_fleet_is_deterministic_and_mixed():
    a = generate_fleet(30, 4, 0.8, random.Random(1))
    b = generate_fleet(30, 4, 0.8, random.Random(1))
    assert [x.agent_id for x in a] == [x.agent_id for x in b]
    assert [x.role for x in a] == [x.role for x in b]
    # An equal mix draws from all three archetypes.
    roles = {x.role for x in a}
    assert roles <= {p.name for p in PROFILES}
    assert len(roles) >= 2


def test_overconfident_archetype_over_predicts_success():
    # An overconfident agent's self-report exceeds its true success on average.
    fleet = generate_fleet(60, 4, 0.8, random.Random(3), mix={"overconfident": 1.0})
    tasks = generate_tasks(40, 4, random.Random(4), 0.2)
    client = FleetClient(seed=5)
    gaps = []
    for a in fleet[:20]:
        for t in tasks[:10]:
            from cta.scoring import compatibility

            true_success = compatibility(a, t) * a.capability
            gaps.append(client.assess(a, t) - true_success)
    assert statistics.mean(gaps) > 0.05


def test_reliability_bins_diagonal_for_perfect_predictor():
    # A predictor whose value equals the outcome sits on the diagonal in each bin.
    bins = reliability_bins([1.0, 1.0, 0.0, 0.0], [1.0, 1.0, 0.0, 0.0])
    assert bins  # both a low and a high bin are populated
    for b in bins:
        assert abs(b["mean_prediction"] - b["accuracy"]) < 1e-9
    # An overconfident predictor sits below the diagonal (prediction > accuracy).
    over = reliability_bins([0.9, 0.9, 0.9, 0.9], [1.0, 0.0, 0.0, 0.0])
    assert over[0]["mean_prediction"] > over[0]["accuracy"]


def test_fleet_correction_recovers_completion():
    exp = fleet_experiment(seeds=4)
    assert exp["reliability_completion"] > exp["raw_completion"]
    assert exp["bins_raw"] and exp["bins_reliability"]


def test_fleet_mix_sweep_recovers_across_compositions():
    sweep = fleet_mix_sweep(seeds=3, fractions=(0.0, 1.0))
    # The correction recovers completion at both ends of the composition range.
    assert all(p["recovery"] > 0.0 for p in sweep)
