"""The ACP broker: JSON-RPC dispatch, routing decisions, and self-improvement."""

from cta.acp import (
    AcpBroker,
    clamp_gate,
    make_fleet_downstream,
    prior_bidder,
    probe_bidder,
)
from cta.wrappers import Fleet, Model


def _fleet():
    return Fleet(models=[
        Model(name="haiku", tier="economy"),
        Model(name="sonnet", tier="standard"),
        Model(name="opus", tier="premium"),
    ])


def _new(broker):
    return broker.handle({"jsonrpc": "2.0", "id": 1, "method": "session/new", "params": {}})[
        "result"
    ]["sessionId"]


def _prompt(broker, sid, task):
    return broker.handle({
        "jsonrpc": "2.0", "id": 2, "method": "session/prompt",
        "params": {"sessionId": sid, "taskType": task,
                   "prompt": [{"type": "text", "text": f"do {task}"}]},
    })


def test_initialize_and_new_session():
    broker = AcpBroker(_fleet())
    init = broker.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
    assert init["result"]["protocolVersion"] == AcpBroker.PROTOCOL_VERSION
    assert init["result"]["agentCapabilities"]["promptCapabilities"]["routing"] is True
    assert _new(broker) == "s0"


def test_prompt_streams_routing_decision_and_reply():
    notes = []
    fleet = _fleet()
    # A cheap model with a proven track record clears the barrier and wins.
    for _ in range(6):
        fleet.record("haiku", "sort", True)
    broker = AcpBroker(fleet, notify=notes.append)
    sid = _new(broker)
    resp = _prompt(broker, sid, "sort")["result"]
    assert resp["routedTo"] == "haiku"
    assert resp["stopReason"] == "end_turn"
    updates = [n["params"]["update"] for n in notes]
    kinds = [u["type"] for u in updates]
    assert "routing_decision" in kinds and "agent_message_chunk" in kinds
    dec = next(u for u in updates if u["type"] == "routing_decision")
    assert dec["model"] == "haiku" and "haiku" in dec["eligible"]


def test_unknown_method_and_session_error():
    broker = AcpBroker(_fleet())
    assert broker.handle({"jsonrpc": "2.0", "id": 1, "method": "bogus"})["error"]["code"] == -32601
    # prompt on an unknown session surfaces a JSON-RPC error, not a crash.
    err = _prompt(broker, "nope", "sort")
    assert err["error"]["code"] == -32603


def test_cancel_is_a_notification():
    broker = AcpBroker(_fleet())
    sid = _new(broker)
    cancel = {"jsonrpc": "2.0", "method": "session/cancel", "params": {"sessionId": sid}}
    assert broker.handle(cancel) is None


def test_track_record_makes_routing_self_improve():
    fleet = _fleet()
    broker = AcpBroker(fleet)
    sid = _new(broker)
    # Cold start: no model clears the barrier, so it escalates to the frontier.
    first = _prompt(broker, sid, "sort")["result"]
    assert first["routedTo"] == "opus"
    # A deployment accrues an economy track record on this task type; routing then
    # drops to the cheapest model without any privileged information.
    for _ in range(6):
        fleet.record("haiku", "sort", True)
    later = _prompt(broker, sid, "sort")["result"]
    assert later["routedTo"] == "haiku"


# --- Phase 2A: elicitation, gate, multi-downstream -----------------------------


def test_probe_bidder_elicits_and_clamps_per_candidate():
    calls = []

    def probe(model, task_type):
        calls.append((model, task_type))
        return {"haiku": 1.5, "sonnet": 0.8, "opus": -0.2}[model]  # out-of-range on purpose

    bids = probe_bidder(probe)("sort", _fleet())
    assert bids == {"haiku": 1.0, "sonnet": 0.8, "opus": 0.0}  # clamped into [0,1]
    assert len(calls) == 3  # one probe turn per candidate: the measured overhead


def test_clamp_gate_sanitises_raw_bids():
    gated = clamp_gate({"haiku": 2.0, "sonnet": 0.5, "opus": -1.0}, _fleet())
    assert gated == {"haiku": 1.0, "sonnet": 0.5, "opus": 0.0}


def test_probe_mode_routing_surfaces_raw_bids():
    # A probe that reports a proven-cheap model confident routes the turn to it.
    fleet = _fleet()
    for _ in range(6):
        fleet.record("haiku", "sort", True)
    notes = []
    broker = AcpBroker(fleet, notify=notes.append, bidder=probe_bidder(lambda m, t: 0.9))
    sid = _new(broker)
    resp = _prompt(broker, sid, "sort")["result"]
    assert resp["routedTo"] == "haiku"
    dec = next(n["params"]["update"] for n in notes
               if n["params"]["update"]["type"] == "routing_decision")
    assert dec["rawBids"]["haiku"] == 0.9  # the elicited self-report is surfaced


def test_make_fleet_downstream_dispatches_per_model():
    seen = []

    def solver_for(tag):
        def _solve(model, task_type, prompt_text):
            seen.append(tag)
            return (f"{tag} did {task_type}", True)
        return _solve

    downstream = make_fleet_downstream(
        {"haiku": solver_for("A"), "opus": solver_for("B")},
        default=solver_for("D"),
    )
    assert downstream("haiku", "sort", "")[0] == "A did sort"
    assert downstream("sonnet", "sort", "")[0] == "D did sort"  # falls back to default
    assert seen == ["A", "D"]


def test_prior_bidder_default_matches_tier_priors():
    bids = prior_bidder()("sort", _fleet())
    assert bids == {"haiku": 0.85, "sonnet": 0.92, "opus": 0.96}
