"""Concurrent multi-process claiming over the SQLite store (P3.1).

The simulation engines model decentralised coordination; this drives the real
atomic claim from several operating-system processes at once, so the claim's
correctness is demonstrated under genuine contention rather than assumed. Each
worker is its own process with its own connection to the shared WAL database, and
the store's ``BEGIN IMMEDIATE`` conditional update is the only thing serialising
them. The invariant under test: every task is claimed by exactly one worker, no
matter how many race for it.
"""

from __future__ import annotations

import multiprocessing as mp
import time
from pathlib import Path

from cta.store import Store


def _claim_worker(db_path: str, agent_id: str, task_ids: list[str], out_q) -> None:
    """One process: try to claim every task, report which ones this worker won."""
    store = Store(db_path)
    won = [tid for tid in task_ids if store.claim(tid, agent_id)]
    out_q.put((agent_id, won))


def run_concurrent_claim(n_workers: int, n_tasks: int, db_path: str | Path) -> dict[str, float]:
    """Advertise ``n_tasks`` and let ``n_workers`` processes race to claim them.

    Returns the number of distinct tasks claimed, any double claims (must be zero),
    the count the database itself reports as CLAIMED, and the wall-clock throughput.
    """
    store = Store(db_path)
    store.init_schema()
    task_ids = [f"task_{i}" for i in range(n_tasks)]
    for tid in task_ids:
        store.add_task(tid, {"domain": "coding"})
        store.advertise(tid)

    ctx = mp.get_context("spawn")
    out_q: mp.Queue = ctx.Queue()
    procs = [
        ctx.Process(target=_claim_worker, args=(str(db_path), f"agent_{k}", task_ids, out_q))
        for k in range(n_workers)
    ]
    t0 = time.perf_counter()
    for p in procs:
        p.start()
    # Drain the queue before joining so a full pipe buffer cannot deadlock a worker.
    results = [out_q.get() for _ in range(n_workers)]
    for p in procs:
        p.join()
    elapsed = time.perf_counter() - t0

    all_won = [tid for _, won in results for tid in won]
    unique = set(all_won)
    db_claimed = int(store.count_by_status().get("CLAIMED", 0))
    return {
        "workers": n_workers,
        "tasks": n_tasks,
        "claimed": len(all_won),
        "unique_claimed": len(unique),
        "double_claims": len(all_won) - len(unique),
        "db_claimed": db_claimed,
        "throughput": len(all_won) / elapsed if elapsed > 0 else 0.0,
        "elapsed": elapsed,
    }


def concurrency_sweep(
    worker_counts: tuple[int, ...], n_tasks: int, db_dir: str | Path
) -> list[dict[str, float]]:
    """Run the concurrent claim at several worker counts, one fresh database each.

    Reports throughput against the number of contending processes and confirms the
    no-double-claim invariant holds at every level.
    """
    out: list[dict[str, float]] = []
    for w in worker_counts:
        db_path = Path(db_dir) / f"concurrent_{w}.db"
        out.append(run_concurrent_claim(w, n_tasks, db_path))
    return out
