"""Tests for visualisation, the report generator, and the autorun command."""

import json

from cta.cli import autorun
from cta.report import evaluate
from cta.viz import line_chart


def test_line_chart_is_svg():
    svg = line_chart(
        {"a": [(1.0, 2.0), (2.0, 3.0)], "b": [(1.0, 1.0), (2.0, 4.0)]},
        title="t",
        xlabel="x",
        ylabel="y",
    )
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "polyline" in svg or "path" in svg


def test_evaluate_returns_all_hypotheses():
    base = {
        "cta": {"mean_quality": [0.85, 0.86, 0.84]},
        "pull_based": {"mean_quality": [0.80, 0.79, 0.81]},
        "central_optimal": {"mean_quality": [0.88, 0.87, 0.89]},
    }
    scaling = {
        "cta": [{"n_agents": 40, "mean": 100.0}, {"n_agents": 320, "mean": 300.0}],
        "central_optimal": [{"n_agents": 40, "mean": 1600.0}, {"n_agents": 320, "mean": 100000.0}],
    }
    hetero = {
        "cta": [{"heterogeneity": 0.0, "mean": 0.70}, {"heterogeneity": 1.0, "mean": 0.90}],
        "central_optimal": [
            {"heterogeneity": 0.0, "mean": 0.75},
            {"heterogeneity": 1.0, "mean": 0.80},
        ],
    }
    verdicts = evaluate(base, scaling, hetero)
    assert set(verdicts.keys()) == {"H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8"}
    assert verdicts["H1"]["verdict"] == "SUPPORTED"  # central grows faster
    assert verdicts["H6"]["verdict"] == "SUPPORTED"  # advantage rises with heterogeneity
    # Without calibration or safety data the new hypotheses are pending, not evaluated.
    assert verdicts["H7"]["verdict"] == "PENDING"
    assert verdicts["H8"]["verdict"] == "PENDING"


def test_autorun_writes_artifacts(tmp_path):
    out = tmp_path / "results"
    summary = autorun(str(out), demo=True)
    assert (out / "summary.json").is_file()
    assert (out / "RESULTS.md").is_file()
    assert (out / "figures" / "scaling_peak_per_node.svg").is_file()
    assert (out / "figures" / "heterogeneity_quality.svg").is_file()
    assert (out / "figures" / "calibration_quality.svg").is_file()
    assert (out / "figures" / "annealing_stall.svg").is_file()
    loaded = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert "verdicts" in loaded and "scaling_peak_per_node" in loaded
    assert "calibration" in loaded and "safety" in loaded
    assert "annealing" in loaded and "temporal" in loaded
    assert summary["verdicts"]["H1"]["verdict"] in ("SUPPORTED", "NOT SUPPORTED")
    # The calibration, safety, and annealing hypotheses are evaluated by the full run.
    assert summary["verdicts"]["H7"]["verdict"] == "SUPPORTED"
    assert summary["verdicts"]["H8"]["verdict"] == "SUPPORTED"
    assert summary["verdicts"]["H4"]["verdict"] == "SUPPORTED"
    assert summary["verdicts"]["H5"]["verdict"] == "SUPPORTED"
