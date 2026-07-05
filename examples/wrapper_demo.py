"""Demo: the CTA wrapper layer routing a fleet, from `cta.wrappers`.

Runs offline and deterministically, no model calls. It shows the two product
wrappers on a small task set that mirrors the real-agent finding: with only a
coarse track record the router sends a hard task to a cheap model that fails it,
and with a per-task track record it escalates exactly that task to a stronger
model, holding completion at the frontier level for a fraction of the cost.

    python -m examples.wrapper_demo
"""

from __future__ import annotations

from cta.wrappers import Fleet, Model, cost_saving, route, wrap_task

# A cheap-to-expensive fleet at the representative price tiers.
FLEET_MODELS = [
    Model("haiku", "economy"),
    Model("sonnet", "standard"),
    Model("opus", "premium"),
]

TASKS = ["fraction_to_decimal", "calculate3", "min_window", "is_match"]

# Ground-truth: the cheap model is competent except on the hardest task; the
# stronger models pass everything. (This mirrors the measured expert-tier result.)
PASSES = {
    "haiku": {"fraction_to_decimal": True, "calculate3": True, "min_window": True,
              "is_match": False},
    "sonnet": {t: True for t in TASKS},
    "opus": {t: True for t in TASKS},
}
# Every model is confident on every task (self-reports are not the problem).
BIDS = {t: {"haiku": 0.9, "sonnet": 0.9, "opus": 0.92} for t in TASKS}
TOKENS = 4000.0


def _run(fleet: Fleet, label: str) -> None:
    routed, plan = [], []
    for task in TASKS:
        d = route(task, BIDS[task], fleet)
        routed.append((d.model, TOKENS))
        plan.append((task, d.model, PASSES[d.model][task]))
    completion = sum(1 for _, _, ok in plan if ok) / len(plan)
    saving = cost_saving(routed, fleet, TOKENS)
    print(f"\n{label}")
    for task, model, ok in plan:
        print(f"  {task:20} -> {model:7} {'pass' if ok else 'FAIL'}")
    print(f"  completion {completion:.2f} | cost {saving['saving_multiple']}x cheaper "
          f"than always-{fleet.most_capable().name}")


def main() -> None:
    # The task wrapper: a loose task becomes an explicit contract.
    contract = wrap_task(
        "is_match",
        "def is_match(s: str, p: str) -> bool:",
        "Wildcard match: '?' any single char, '*' any sequence including empty.",
        acceptance=["'*' can match the empty string", "the match must cover all of s and p"],
        self_check=["('aa','*') -> True", "('acdcb','a*c?b') -> False"],
    )
    print("TASK WRAPPER — the contract an agent receives:\n")
    print(contract.envelope())

    print("\n\nAGENT WRAPPER — routing the same fleet two ways:")

    # 1) Coarse track record: one scalar per model (good overall), so the router
    #    trusts the cheap model on the hard task and loses completion.
    coarse = Fleet(models=[Model(m.name, m.tier) for m in FLEET_MODELS])
    scalar = {"haiku": 0.85, "sonnet": 0.9, "opus": 0.92}
    for m in ("haiku", "sonnet", "opus"):
        for t in TASKS:
            coarse.reliability.setdefault(m, {})[t] = scalar[m]
    _run(coarse, "1) coarse track record (one scalar per model)")

    # 2) Per-task track record: the finer history a deployment accumulates. Haiku's
    #    is_match reliability is low, so the router escalates just that task.
    fine = Fleet(models=[Model(m.name, m.tier) for m in FLEET_MODELS])
    for m in ("haiku", "sonnet", "opus"):
        for t in TASKS:
            fine.reliability.setdefault(m, {})[t] = 0.9 if PASSES[m][t] else 0.35
    _run(fine, "2) per-task track record (escalates exactly the unreliable task)")

    print("\nThe task wrapper makes the cheap model reliable; the agent wrapper, given\n"
          "a per-task track record, routes to it and escalates only what it must.")


if __name__ == "__main__":
    main()
