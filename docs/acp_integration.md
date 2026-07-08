# Including the Agent Client Protocol (ACP) in CTA

Plan for wiring the calibration-robust orchestrator into the Agent Client
Protocol, so the research runs inside a real editor-agent protocol with real
agents. This is a design + engineering plan; it is not started yet.

## What ACP is (from the Zed live-coding talk, Bennet Fenner)

ACP is a JSON-RPC protocol, in the spirit of LSP and MCP, that lets any coding
agent talk to any compatible editor/client, removing bespoke integrations.

- **Transport:** JSON-RPC 2.0 over stdio, local today; remote (HTTP/WebSocket) is
  JetBrains-backed WIP. Reuses MCP JSON representations where possible.
- **Ecosystem:** open (agentclientprotocol.com), ~40 clients (Zed, JetBrains,
  Obsidian, ...), agents via native CLI modes or adapters.
- **Four core methods an agent must implement:** `initialize` (negotiate
  capabilities/version), `session/new` (open a stateful session), `prompt` (send
  content blocks for a session), `cancel` (abort a running turn).
- **Session updates** (async agent -> client notifications outside the
  request/response loop): `agent_message_chunk` (stream tokens), `tool_call`
  (metadata + `in_progress`/final states), a **diff** content type
  (`old_text`/`new_text`, client renders it), and plan updates.
- **Filesystem proxying:** the agent calls `fs/readTextFile` / `fs/writeTextFile`
  over ACP instead of the OS, so it sees the editor's unsaved ("dirty") buffers.
- **Terminal management:** clients advertise a terminal capability the agent can
  drive natively.
- **ACP vs MCP:** MCP gives an agent *tools*; ACP gives an agent an *editor*.
  Complementary, different layers.

## Why this matters for CTA specifically

Two payoffs, one strategic:

1. **Distribution for the agent-wrapper product.** `cta.wrappers.route()` already
   turns self-reported bids + a `Fleet` into a `RouteDecision`. Exposed as an ACP
   agent, that router becomes usable inside ~40 editors with no bespoke work.
2. **The publication lever (the big one).** The honest gap for a top-tier venue
   is "no head-to-head against real routers on real agents." ACP closes it: it is
   a real protocol where we can elicit **real self-reports from real agents**,
   apply the track-record correction + integrity gate, route live, and measure
   completion vs a naive-self-report router and a single-agent baseline -- on the
   same tasks, in the same editor. The calibration thesis (miscalibrated
   self-reports, recovered by a track-record correction) gets a live, external
   demonstration instead of a synthetic one.

## Architecture: CTA as an ACP broker

CTA presents **as an ACP agent to the editor** while acting **as an ACP client to
a downstream fleet** -- a routing man-in-the-middle.

```
  Editor (Zed/JetBrains)            CTA broker                 Downstream fleet
        │   ACP agent iface   ┌───────────────────────┐  ACP client iface
        ├────────────────────>│ initialize/session/   │──────> Agent A (e.g. Claude Code ACP)
        │  prompt(session,     │ prompt/cancel handlers│──────> Agent B (e.g. Gemini CLI ACP)
        │   content blocks)    │  + cta.wrappers.route │──────> Model tiers (Haiku/Sonnet/Opus)
        │<────────────────────┤  + track-record corr. │<─────  session updates proxied back
        │  session updates     │  + integrity gate     │
        │  (chunks/tool/diff)  └───────────────────────┘
```

Start tractable (**one runtime, multiple model tiers** as the fleet) and only
later reach for the ambitious version (**heterogeneous agent products** each
speaking ACP).

## Mapping ACP primitives to CTA components

| ACP primitive | CTA role | Existing code |
|---------------|----------|---------------|
| `initialize` | advertise a routing meta-agent; negotiate version/caps | new `acp/agent.py` |
| `session/new` | open a routing session; lazily open downstream sessions | new `acp/broker.py` |
| `prompt` turn | **the auction unit**: elicit bids, correct, gate, select, forward | `wrappers.route()`, `harness`, `engine` |
| self-report bids | elicited per turn (see loop below); corrected before use | `wrappers.route(bids=...)` |
| track-record correction + integrity gate | reweight/validate raw self-reports | `routing.py`, `engine.py` |
| `session/update` | proxy chosen agent's stream back; inject a routing-decision update | new `acp/broker.py` |
| `cancel` | propagate to the active downstream session | `acp/broker.py` |
| `fs/*`, `terminal` | pass-through editor <-> chosen downstream | `acp/broker.py` |
| outcome capture | record pass/accept into the track record, closing the loop | `store.py`, `scoring.py` |

## The prompt-turn allocation loop over ACP

1. Editor sends `prompt(session_id, content_blocks)`.
2. Broker elicits calibrated self-reports for the candidate fleet:
   - **Probe mode** -- send a lightweight confidence-probe prompt to each
     candidate, parse a bid in [0,1]. Real self-report; costs one cheap extra
     turn per candidate.
   - **Prior mode** -- derive a bid from task features + each candidate's track
     record only (no probe). Cheaper, no live self-report.
   ACP has no native confidence field, so this elicitation is a deliberate CTA
   extension; its latency/token overhead is measured and reported.
3. Apply the track-record correction to raw bids; apply the integrity gate
   (drop/penalise implausible bids). This is the paper's mechanism, live.
4. `route(task_type, corrected_bids, fleet)` selects the winner.
5. Forward the real prompt to the winner's downstream session; proxy its
   `session/update` stream (chunks, `tool_call`, diffs) back to the editor,
   tagged with a routing-decision update ("routed to X, corrected conf 0.yz").
6. On turn end, record the outcome (hidden-test pass / user diff-accept) into the
   track record -- closing the calibration loop for the next turn.
7. `cancel` propagates to the active downstream.

## Next steps (Phase 4), tagged by usage cost

Most of this is engineering with **no subagent solves**, so it can proceed during
low-usage windows; only the evaluation is metered.

| Step | What | Usage |
|------|------|-------|
| P4.0 | This design doc; pin a spec version; choose stdlib JSON-RPC-over-stdio (keep the repo single-language Python) | free |
| P4.1 | Minimal ACP **agent** skeleton: `initialize`/`session/new`/`prompt`/`cancel` + `agent_message_chunk` streaming; echo agent that handshakes with a real client (Zed) and a local conformance harness | free |
| P4.2 | Wire `wrappers.route()` into the `prompt` handler with a **simulated** downstream; routing-decision update visible in the editor | free |
| P4.3 | CTA as ACP **client** to **one** real downstream agent, end-to-end proxying of chunks/tool_call/diff | small smoke-test usage |
| P4.4 | Confidence **elicitation** (probe + prior modes) + track-record correction + integrity gate, live on the turn | free plumbing |
| P4.5 | **Multi-downstream** routing across the model-tier fleet (heterogeneous agent products deferred) | free plumbing |
| P4.6 | **Evaluation harness + head-to-head**: run `expert_suite`/`project` tasks through the broker; CTA-corrected routing vs naive-self-report routing vs always-frontier vs single-agent; report completion, cost, and the probe overhead | **metered -- batch like Phase 3** |
| P4.7 | Paper section "ACP-native calibration-robust routing" + product/README for the ACP agent | free |

## Sequencing against Phase 3

Phase 3 (real CIs + the two-sided calibration curve) is the committed,
reviewer-driven work and banks first. But P4.0-P4.5 are pure plumbing with no
solve budget, so they are a **good use of a usage-constrained window** -- build
the broker while Phase 3's metered runs wait for resets. P4.6 (the metered
head-to-head) comes after Phase 3's asks are banked, and batches across sessions
the same way.

## Risks and honest limitations

- **Young protocol.** ACP shipped Aug 2025 and is evolving; remote transport is
  WIP. Pin a spec version and stay on local stdio first.
- **Python tooling immaturity.** The reference libs are Rust/TS. Recommend
  hand-rolling the JSON-RPC stdio layer in stdlib Python to keep one language;
  fall back to a thin TS adapter only if needed.
- **Confidence is not native to ACP.** Eliciting it costs an extra turn per
  candidate (probe mode). This is a real latency/cost trade-off -- measure it and
  let the track-record correction justify it (ties to the H12 cost-efficiency
  claim).
- **Heterogeneous-agent routing is the payoff but the hard part.** Each downstream
  must speak ACP. Start with one runtime / multiple model tiers; treat
  cross-product routing as a stretch.
- **Testing needs a real client.** Use Zed, and also build a minimal ACP client
  harness -- it doubles as the conformance test.
- **Scope creep.** Hold the first milestone to strictly "handshake + a visible
  routing decision in a real client." Everything else follows only once that is
  green.
