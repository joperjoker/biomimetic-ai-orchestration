"""The opt-in live pilot: a swarm of Claude Code subagents (interface only).

This module defines the interface for Stage 2, the live pilot, but does not make
any model calls. Running it needs the ``llm`` extra and an environment with
Claude Code subagents, and it is gated behind a human approval of the cost
budget. The simulation (Stage 1) uses the same scoring module, so the pilot only
swaps synthetic agents for live ones.

The intended flow per subagent:
1. Read the advertised tasks from the store.
2. The wrapper computes compatibility from the subagent's real role, skills, and
   prompt against each task (this is the calibration under study, E13).
3. Fire when compatibility reaches the task's activation energy.
4. Attempt the atomic claim; on winning, present the plan to the Rejection Gate.
5. If admitted, execute the scoped software micro-task in an isolated git
   worktree and report the test pass fraction as the realised quality.
"""

from __future__ import annotations

from typing import Protocol


class PilotAgent(Protocol):
    """The contract a live subagent worker must satisfy."""

    agent_id: str

    def role(self) -> str: ...
    def skills(self) -> frozenset[str]: ...
    def prompt(self) -> str: ...
    def execute(self, task_id: str, worktree: str) -> float:
        """Run the task in an isolated worktree and return the test pass fraction."""
        ...


def run_pilot(*_args: object, **_kwargs: object) -> None:
    """Placeholder entry point. The live pilot is opt-in and not yet wired.

    Raises to prevent accidental cost. Implement against the store and Claude Code
    subagents when the pilot is approved (see docs/roadmap.md, Phase 7).
    """
    raise NotImplementedError(
        "The live pilot is opt-in and not yet implemented. It requires the llm "
        "extra, Claude Code subagents, and human approval of the cost budget."
    )
