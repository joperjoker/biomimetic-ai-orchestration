"""A minimal Agent Client Protocol (ACP) broker over the CTA agent wrapper.

ACP (Zed Industries, 2025) is a JSON-RPC protocol that lets any editor talk to
any coding agent. This module presents CTA *as* an ACP agent while acting as a
router over a fleet of downstream models: on every ``session/prompt`` turn it
elicits a self-report bid per model, corrects it by the observable track record,
picks the cheapest model that clears the activation barrier
(``cta.wrappers.route``), streams the chosen model's reply back as ``session/update``
notifications, and updates the persistent reliability table so the router
self-improves across turns (the deployment form of H13).

The core is ``AcpBroker.handle(request) -> response``, which is transport-free and
unit-testable; ``serve()`` is a thin newline-delimited-JSON stdio driver for a
real editor. The downstream is pluggable: a simulated one ships here (P4.2), and
a real ACP-client downstream or the benchmark head-to-head harness swaps in via
the ``downstream`` callback.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

from cta.wrappers import Fleet, route

# A downstream solves a task for a chosen model and returns (reply_text, passed).
Downstream = Callable[[str, str, str], "tuple[str, bool]"]
# A notification sink receives JSON-RPC notification dicts (session/update).
Notify = Callable[[dict[str, Any]], None]

# Per-tier self-report a model states before its track record is applied. These
# are the raw bids; the router discounts them by reliability. Cheaper tiers are a
# touch less confident, matching the ladder.
_TIER_SELF_REPORT = {"economy": 0.85, "standard": 0.92, "premium": 0.96}


def _simulated_downstream(model: str, task_type: str, prompt_text: str) -> tuple[str, bool]:
    """Stand-in downstream: the chosen model 'solves' the task and passes."""
    return (f"[{model}] completed task '{task_type}'.", True)


def _error(rid: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


class AcpBroker:
    """CTA presented as an ACP agent that routes over a downstream fleet."""

    PROTOCOL_VERSION = 1

    def __init__(
        self,
        fleet: Fleet,
        notify: Notify | None = None,
        downstream: Downstream | None = None,
    ) -> None:
        self.fleet = fleet
        self._notify = notify or (lambda _n: None)
        self._downstream = downstream or _simulated_downstream
        self._sessions: dict[str, dict[str, Any]] = {}
        self._next = 0
        self.turns: list[dict[str, Any]] = []  # a record of routed turns, for analysis

    # --- JSON-RPC dispatch ---------------------------------------------------

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Handle one JSON-RPC request; return a response, or None for a notification."""
        method = request.get("method")
        params = request.get("params") or {}
        rid = request.get("id")
        try:
            if method == "initialize":
                result: Any = self._initialize(params)
            elif method == "session/new":
                result = self._session_new(params)
            elif method == "session/prompt":
                result = self._prompt(params)
            elif method == "session/cancel":
                self._cancel(params)
                return None  # a notification carries no response
            else:
                return _error(rid, -32601, f"method not found: {method}")
        except Exception as exc:  # noqa: BLE001 - surface as a JSON-RPC error
            return _error(rid, -32603, str(exc))
        if rid is None:
            return None
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    # --- ACP methods ---------------------------------------------------------

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "agentCapabilities": {
                "promptCapabilities": {"routing": True, "trackRecord": True},
            },
        }

    def _session_new(self, params: dict[str, Any]) -> dict[str, Any]:
        sid = f"s{self._next}"
        self._next += 1
        self._sessions[sid] = {"cancelled": False}
        return {"sessionId": sid}

    def _cancel(self, params: dict[str, Any]) -> None:
        sid = params.get("sessionId")
        if sid in self._sessions:
            self._sessions[sid]["cancelled"] = True

    def _elicit_bids(self, task_type: str) -> dict[str, float]:
        """Prior-mode elicitation: each model's raw self-report before correction."""
        return {m.name: _TIER_SELF_REPORT.get(m.tier, 0.9) for m in self.fleet.models}

    def _prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        sid = params.get("sessionId")
        if sid not in self._sessions:
            raise ValueError(f"unknown sessionId: {sid}")
        blocks = params.get("prompt") or []
        text = " ".join(
            b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"
        )
        task_type = params.get("taskType") or (text.split()[0] if text.split() else "task")

        bids = self._elicit_bids(task_type)
        decision = route(task_type, bids, self.fleet)

        # Stream the routing decision, then the chosen model's reply, as ACP updates.
        self._emit(sid, {
            "type": "routing_decision",
            "model": decision.model,
            "correctedBids": {k: round(v, 3) for k, v in decision.corrected_bids.items()},
            "eligible": decision.eligible,
            "reason": decision.reason,
        })
        reply, passed = self._downstream(decision.model, task_type, text)
        self._emit(sid, {"type": "agent_message_chunk", "content": {"type": "text", "text": reply}})

        # Update the persistent track record from the realised outcome (H13 in
        # deployment): the next turn's routing carries a sharper signal.
        self.fleet.record(decision.model, task_type, passed)
        self.turns.append({"task": task_type, "model": decision.model, "passed": passed})
        return {"stopReason": "end_turn", "routedTo": decision.model, "passed": passed}

    def _emit(self, sid: str, update: dict[str, Any]) -> None:
        self._notify({
            "jsonrpc": "2.0",
            "method": "session/update",
            "params": {"sessionId": sid, "update": update},
        })


def serve(fleet: Fleet, stdin=None, stdout=None) -> None:  # pragma: no cover - stdio loop
    """Newline-delimited-JSON stdio driver for a real ACP client.

    One JSON object per line in and out (a simple framing; Content-Length framing
    can be layered on without touching the broker). Notifications are written to
    stdout as they are emitted during a turn.
    """
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout

    def _write(obj: dict[str, Any]) -> None:
        stdout.write(json.dumps(obj) + "\n")
        stdout.flush()

    broker = AcpBroker(fleet, notify=_write)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            _write(_error(None, -32700, "parse error"))
            continue
        response = broker.handle(request)
        if response is not None:
            _write(response)
