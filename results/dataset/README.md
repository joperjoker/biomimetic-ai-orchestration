# Raw run dataset

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
