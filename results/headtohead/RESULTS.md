# Head-to-head on real agents (leave-one-replicate-out replay)

Ladder `bare` outcomes, 10 folds. Reliability
and self-reports are estimated from the training replicates only; each policy
is scored on the held-out replicate it did not see.

| policy | completion (95% CI) | cost per task-set (USD) |
|--------|---------------------|-------------------------|
| CTA (corrected) | 0.988 [0.963, 1.000] | 0.05700 |
| naive self-report | 0.950 [0.912, 0.988] | 0.02400 |
| always frontier | 1.000 [1.000, 1.000] | 1.44000 |
| single cheapest | 0.950 [0.912, 0.988] | 0.02400 |

- Completion gain over naive self-report: **+0.037**.
- Completion retained versus always-frontier: **-0.013**.
- Cost saving versus always-frontier: **25.26x**.
