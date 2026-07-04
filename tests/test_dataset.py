"""The raw run dataset round-trips and re-derives a headline aggregate."""

import csv
import statistics

from cta.dataset import COLUMNS, build_rows, dump_runs
from cta.harness import CONDITIONS, CellParams, Protocol, run_seeds


def _proto() -> Protocol:
    return Protocol(seeds=4, base=CellParams(n_agents=30, n_tasks=24, n_domains=3))


def test_build_rows_covers_every_condition_and_seed():
    proto = _proto()
    rows = build_rows(proto)
    base = [r for r in rows if r["block"] == "base"]
    # One base row per (condition, seed).
    assert len(base) == len(CONDITIONS) * proto.seeds
    assert {r["condition"] for r in base} == set(CONDITIONS)
    # The bounded staleness block records both series across the staleness sweep.
    stale = [r for r in rows if r["block"] == "bounded_staleness"]
    assert stale and {r["condition"] for r in stale} == {"cta", "central_bounded"}


def test_csv_round_trips_and_reproduces_a_headline_mean(tmp_path):
    proto = _proto()
    path = dump_runs(str(tmp_path), proto)
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == list(COLUMNS)
        loaded = list(reader)
    # Re-derive the CTA base mean quality from the CSV and check it matches a
    # fresh aggregate of the same runs.
    csv_cta = [
        float(r["mean_quality"])
        for r in loaded
        if r["block"] == "base" and r["condition"] == "cta"
    ]
    fresh = [r["mean_quality"] for r in run_seeds("cta", proto.base, proto.seeds)]
    assert len(csv_cta) == proto.seeds
    assert abs(statistics.fmean(csv_cta) - statistics.fmean(fresh)) < 1e-6
    # The data dictionary ships alongside the CSV.
    assert (path.parent / "README.md").is_file()
