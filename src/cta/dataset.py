"""Release the raw per-run simulation dataset as CSV.

Every headline number in the paper is a mean over seeded replications. This
module writes the underlying per-seed, per-condition rows to a flat CSV so a
reader can re-derive any aggregate, refit any curve, or run their own tests, with
no dependency beyond the standard library. It is the raw form of the evidence,
not a summary of it.
"""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

from cta.harness import CONDITIONS, Protocol, bounded_vs_cta, run_cell

# The columns written for each run, in a stable order. Inputs first, then
# outcomes, then the coordination-load fields.
COLUMNS = (
    "block",
    "condition",
    "seed",
    "family",
    "n_agents",
    "n_tasks",
    "staleness",
    "mean_quality",
    "completion_rate",
    "stall_rate",
    "infeasible_rate",
    "integrity_violations",
    "peak_per_node",
    "coordinator_work",
)


def _row(block: str, condition: str, seed: int, params, summary: dict) -> dict:
    return {
        "block": block,
        "condition": condition,
        "seed": seed,
        "family": params.family,
        "n_agents": params.n_agents,
        "n_tasks": params.n_tasks,
        "staleness": params.central_staleness if condition == "central_bounded" else "",
        "mean_quality": round(float(summary.get("mean_quality", 0.0)), 6),
        "completion_rate": round(float(summary.get("completion_rate", 0.0)), 6),
        "stall_rate": round(float(summary.get("stall_rate", 0.0)), 6),
        "infeasible_rate": round(float(summary.get("infeasible_rate", 0.0)), 6),
        "integrity_violations": int(summary.get("integrity_violations", 0)),
        "peak_per_node": int(summary.get("peak_per_node", 0)),
        "coordinator_work": int(summary.get("coordinator_work", 0)),
    }


def build_rows(protocol: Protocol) -> list[dict]:
    """Collect every per-seed run into a flat list of rows.

    Two blocks. ``base`` runs each condition at the base parameters across the
    protocol's seeds. ``bounded_staleness`` records the per-seed CTA and bounded
    central quality at every coordinator staleness level, the raw form of the H9
    curve.
    """
    rows: list[dict] = []
    for condition in CONDITIONS:
        for seed in range(protocol.seeds):
            summary = run_cell(condition, protocol.base, seed)
            rows.append(_row("base", condition, seed, protocol.base, summary))

    for point in bounded_vs_cta(protocol.base, protocol.seeds):
        stale = float(point["staleness"])  # type: ignore[arg-type]
        params = replace(protocol.base, central_staleness=stale)
        for seed, q in enumerate(point["cta_values"]):  # type: ignore[arg-type]
            rows.append(
                _row("bounded_staleness", "cta", seed, params, {"mean_quality": q})
            )
        for seed, q in enumerate(point["bounded_values"]):  # type: ignore[arg-type]
            rows.append(
                _row(
                    "bounded_staleness",
                    "central_bounded",
                    seed,
                    params,
                    {"mean_quality": q},
                )
            )
    return rows


def write_runs_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


_README = """# Raw run dataset

`runs.csv` is the raw per-seed, per-condition output of the simulation, the
evidence under every aggregate in the paper. One row is one run.

## Columns

- `block`: `base` (all conditions at the base parameters) or `bounded_staleness`
  (CTA and the bounded central across coordinator staleness, the H9 curve).
- `condition`: one of `cta`, `pull_based`, `central_greedy`, `central_optimal`,
  `central_best`, `central_bounded`.
- `seed`: the replication seed. All randomness is derived from it, so a row is
  fully reproducible.
- `family`: the generative distribution family (`domains` or `latent`).
- `n_agents`, `n_tasks`: the population sizes for the run.
- `staleness`: for `central_bounded`, how out of date its reliability table is
  (0 fresh, 1 fully stale); blank otherwise.
- `mean_quality`: mean realised quality of completed work (the primary quality
  metric, E12).
- `completion_rate`, `stall_rate`, `infeasible_rate`: task-outcome fractions.
- `integrity_violations`: out-of-scope writes that executed (0 with the gate on).
- `peak_per_node`: the coordination bottleneck, peak per-node evaluations.
- `coordinator_work`: total pair evaluations at the coordinator (`N` times `M`
  for the central conditions).

## Reproduce

```
python -m cta.cli dataset --out results
```

Regenerates `runs.csv` deterministically from seeds.
"""


def dump_runs(out_dir: str, protocol: Protocol | None = None) -> Path:
    """Build the dataset and write ``runs.csv`` and a data dictionary."""
    protocol = protocol or Protocol()
    out = Path(out_dir) / "dataset"
    rows = build_rows(protocol)
    write_runs_csv(out / "runs.csv", rows)
    (out / "README.md").write_text(_README, encoding="utf-8")
    return out / "runs.csv"
