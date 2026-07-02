"""The Auto-Researcher: a propose, evaluate, keep-or-revert loop.

The loop tunes a bounded search space to improve a protected primary metric,
subject to guardrails, exactly the shape of Karpathy's AutoResearch. The default
proposer is a deterministic seeded search, so the loop runs with no LLM and stays
reproducible; an LLM proposer can be substituted without changing the loop or its
guardrails.
"""

from cta.autoresearch.loop import Decision, run_loop
from cta.autoresearch.search_space import SearchPoint, propose

__all__ = ["Decision", "SearchPoint", "propose", "run_loop"]
