"""Print the proof-of-concept report. Run with ``python -m examples.poc``."""

from __future__ import annotations

from examples.poc import run_poc


def main() -> int:
    r = run_poc()
    print("Chemotactic Task Allocation: proof of concept (offline, deterministic)")
    print(f"Fleet: {r['n_agents']} agents, {r['n_tasks']} tasks, half adversarial.\n")
    print("Self-selected allocation (winner chosen by the calibrated, gated bid):")
    for a in r["allocation"]:
        winner = a["winner"] or "-"
        print(f"  {a['task']:>8}  ->  {winner:>8}   [{a['status']}]")
    print()
    print(f"Tasks completed successfully:      {r['completed']}")
    print(f"Out-of-scope actions the gate stopped: {r['prevented_violations']}")
    print(
        f"Coordinator cost: central ${r['central_cost_usd']} at one node vs "
        f"${r['decentralised_per_node_usd']} at the busiest decentralised node "
        f"({r['savings_multiple']}x; the gap widens with N)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
