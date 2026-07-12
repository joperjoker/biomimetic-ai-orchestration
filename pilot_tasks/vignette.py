"""A live end-to-end ACP-broker vignette over real Claude subagents.

This demonstrates the deployed harness of Paper 2: the broker receives a prompt,
elicits a confidence bid per model, corrects it by a persistent per-task track
record, routes to the cheapest model that clears the activation barrier, forwards
the turn to that real model, scores the result against hidden tests, and records
the outcome. It is a vignette, not a benchmark: a handful of turns showing the
routing logic and the ACP ``session/update`` stream on real agents.

The track record is warm-started from the Phase 3 capability-ladder outcomes (the
calibration a deployment already has). With that prior, easy tasks route to the
cheap model and the one task the cheap model is unreliable on (``is_match``, Haiku
reliability $0.7$) escalates: the router protects completion exactly where it
should while paying the cheap price everywhere else.

Flow (orchestrated one-shot subagents supply the metered solves):

1. ``preview()`` prints the routing decision per task (deterministic, no solves),
   so the caller knows which model to spawn.
2. The caller spawns one subagent per task at the routed model, one-shot no tools,
   and saves the returned solution to ``results/vignette/{task}.txt`` (resumable:
   an existing file is reused, so a mid-run stop loses nothing).
3. ``run()`` scores each saved solution, replays the turns through a real
   ``AcpBroker`` whose downstream returns those real outcomes, and writes the ACP
   transcript, a summary, and a routing figure.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from cta.acp import AcpBroker
from cta.cost import PRICING
from cta.viz import bar_chart, save_svg
from cta.wrappers import Fleet, Model
from pilot_tasks.headtohead import _index
from pilot_tasks.ladder import _run, load

OUT = Path("results/vignette")
FIGS = Path("results/figures")
BARRIER = 0.7
TIER = {"haiku": "economy", "sonnet": "standard", "opus": "premium"}
TOKENS_PER_TASK = 4000.0

# The turn stream: four bare task prompts. Function names match the hidden-test
# scorer in pilot_tasks.expert_suite.
TASKS = ["fraction_to_decimal", "multiply_strings", "word_break", "is_match"]
PROMPTS = {
    "fraction_to_decimal": (
        "def fraction_to_decimal(numerator: int, denominator: int) -> str:\n"
        "    # Return numerator/denominator as a decimal string; wrap any repeating\n"
        "    # fractional part in parentheses. numerator 0 returns '0'."
    ),
    "multiply_strings": (
        "def multiply_strings(num1: str, num2: str) -> str:\n"
        "    # Multiply two non-negative integers given as strings and return the\n"
        "    # product as a string, without converting the whole number via int()/float()."
    ),
    "word_break": (
        "def word_break(s: str, words: list[str]) -> bool:\n"
        "    # Return whether s can be segmented into a space-separated sequence of one\n"
        "    # or more words from the list (each word reusable)."
    ),
    "is_match": (
        "def is_match(s: str, p: str) -> bool:\n"
        "    # Wildcard match of pattern p against the whole string s, where '?' matches\n"
        "    # any single character and '*' matches any sequence including empty."
    ),
}


def _blended_rate(tier: str) -> float:
    lo, hi = PRICING[tier]
    return (lo + hi) / 2.0


def warm_fleet() -> Fleet:
    """A fleet whose per-task reliability is warm-started from the ladder data."""
    table = _index(load())
    reps = sorted(table)
    fleet = Fleet(
        models=[Model("haiku", "economy"), Model("sonnet", "standard"), Model("opus", "premium")],
        barrier=BARRIER,
    )
    for m in ("haiku", "sonnet", "opus"):
        fleet.reliability[m] = {}
        for t in TASKS:
            vals = [
                1.0 if table[r][m][t]["passed"] else 0.0
                for r in reps
                if m in table[r] and t in table[r][m]
            ]
            if vals:
                fleet.reliability[m][t] = statistics.fmean(vals)
    return fleet


def _bidder(fleet: Fleet):
    from cta.acp import prior_bidder

    return prior_bidder()


def preview() -> dict[str, str]:
    """Deterministic routing decision per task, before any solve."""
    from cta.wrappers import route

    fleet = warm_fleet()
    tier_bid = {"economy": 0.85, "standard": 0.92, "premium": 0.96}
    bids = {m.name: tier_bid[m.tier] for m in fleet.models}
    out = {}
    for t in TASKS:
        out[t] = route(t, bids, fleet).model
    return out


def _score(task: str) -> tuple[bool, float]:
    """Score the saved solution for ``task`` against the hidden tests."""
    path = OUT / f"{task}.txt"
    if not path.exists():
        raise SystemExit(f"missing solution {path}; spawn the routed subagent first")
    code = path.read_text(encoding="utf-8")
    frac = _run(task, code)
    return frac >= 1.0, frac


def run() -> dict:
    """Replay the turns through a real AcpBroker and write the vignette artifacts."""
    outcomes = {t: _score(t) for t in TASKS}
    fleet = warm_fleet()
    notes: list[dict] = []

    def downstream(model: str, task_type: str, prompt_text: str):
        passed, frac = outcomes[task_type]
        verdict = "passed hidden tests" if passed else f"failed ({frac:.2f} of cases)"
        return (f"[{model}] {verdict} on {task_type}", passed)

    broker = AcpBroker(fleet, notify=notes.append, bidder=_bidder(fleet), downstream=downstream)
    broker.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
    sid = broker.handle({"jsonrpc": "2.0", "id": 1, "method": "session/new", "params": {}})[
        "result"
    ]["sessionId"]

    turns = []
    for i, t in enumerate(TASKS):
        resp = broker.handle({
            "jsonrpc": "2.0", "id": 10 + i, "method": "session/prompt",
            "params": {"sessionId": sid, "taskType": t,
                       "prompt": [{"type": "text", "text": PROMPTS[t]}]},
        })["result"]
        dec = next(
            n["params"]["update"] for n in notes
            if n["params"]["update"]["type"] == "routing_decision"
            and n["params"]["update"].get("model") == resp["routedTo"]
            and not any(x.get("task") == t for x in turns)
        )
        cost = (TOKENS_PER_TASK / 1e6) * _blended_rate(TIER[resp["routedTo"]])
        turns.append({
            "task": t,
            "routed_to": resp["routedTo"],
            "corrected_bids": dec["correctedBids"],
            "reason": dec["reason"],
            "passed": resp["passed"],
            "cost_usd": round(cost, 6),
        })

    _write(turns)
    return {"turns": turns}


def _write(turns: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps({"turns": turns}, indent=2), encoding="utf-8")

    routed_cost = sum(x["cost_usd"] for x in turns)
    frontier_cost = len(turns) * (TOKENS_PER_TASK / 1e6) * _blended_rate("premium")
    saving = round(frontier_cost / routed_cost, 2) if routed_cost else 0.0

    lines = [
        "# Live ACP-broker vignette (real Claude subagents)",
        "",
        "A deployed broker routes each prompt by track-record-corrected confidence,",
        "forwards the turn to the chosen real model, and records the outcome. The",
        "track record is warm-started from the capability-ladder calibration.",
        "",
        "| turn | task | routed to | corrected bids (h/s/o) | outcome |",
        "|------|------|-----------|------------------------|---------|",
    ]
    for i, x in enumerate(turns, 1):
        cb = x["corrected_bids"]
        bids = f"{cb.get('haiku',0):.2f}/{cb.get('sonnet',0):.2f}/{cb.get('opus',0):.2f}"
        outcome = "pass" if x["passed"] else "fail"
        lines.append(f"| {i} | `{x['task']}` | **{x['routed_to']}** | {bids} | {outcome} |")
    lines += [
        "",
        f"- Routed spend: ${routed_cost:.5f} for the {len(turns)} turns; "
        f"always-frontier would cost ${frontier_cost:.5f}: a **{saving}x** saving.",
        "- The barrier is 0.70. Every task whose cheapest corrected bid clears it routes",
        "  cheap; `is_match` (Haiku reliability 0.70, corrected bid below the barrier)",
        "  escalates, protecting completion exactly where the cheap model is unreliable.",
        "",
    ]
    (OUT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")

    # Plot the cheap model's corrected bid per turn: it clears the 0.70 barrier on
    # the first three tasks (so they route cheap) and dips below it on is_match (so
    # the broker escalates to sonnet). The dip below the barrier is the escalation.
    _short = {
        "fraction_to_decimal": "frac_to_dec",
        "multiply_strings": "mult_str",
        "word_break": "word_break",
        "is_match": "is_match",
    }
    cats = [_short.get(x["task"], x["task"]) for x in turns]
    save_svg(
        bar_chart(
            cats,
            {"haiku corrected bid": [
                x["corrected_bids"].get("haiku", 0.0) for x in turns]},
            title="Live broker routing: cheap model's corrected bid vs the 0.70 barrier",
            ylabel="corrected confidence (barrier = 0.70)",
            xlabel="turn (task); is_match falls below and escalates to sonnet",
        ),
        FIGS / "vignette_routing.svg",
    )


if __name__ == "__main__":
    print(json.dumps(preview(), indent=2))
