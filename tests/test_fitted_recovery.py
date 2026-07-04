"""H8 holds when the miscalibration is the measured mixture, not a picked bias."""

from cta.harness import CellParams, fitted_calibration_recovery


def test_reliability_recovers_completion_under_measured_miscalibration():
    base = CellParams(n_agents=60, n_tasks=48, n_domains=4)
    r = fitted_calibration_recovery(base, seeds=8)
    # The track-record correction recovers completion over the raw self-report
    # auction even when each agent's bias is drawn from the measured archetype
    # spread rather than one injected value.
    assert r["reliability_completion"] > r["raw_completion"]
    assert r["recovery"] > 0.1
