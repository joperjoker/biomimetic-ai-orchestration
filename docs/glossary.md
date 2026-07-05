# Glossary: Biology to Engineering Mapping

This glossary maps the biological vocabulary of cryptic female choice onto the engineering concepts of the framework. It is the quick reference for readers who meet a biological term and want its computational meaning.

| Biological term | Engineering concept | Meaning in the framework |
|-----------------|---------------------|--------------------------|
| Egg | Task | The unit of work that advertises itself and is selected for. |
| Chemical signal (chemoattractant) | Scent envelope | The semantic metadata a task emits to attract suitable agents. |
| Sperm | Agent | A distributed worker that approaches tasks and competes for them. |
| Chemotaxis (attraction strength) | Compatibility (c) | How strongly the task wrapper matches an agent's role, skills, and prompt, in [0, 1]. Replaces the abstract signal S. |
| Chemical gradient sensing | Task wrapper | The mechanism that reads an agent's role, skills, and prompt against the task requirements to produce the compatibility score. |
| Gamete fitness | Agent Capability (C) | The agent competence for the required skills. |
| Energetic cost of approach | Latency penalty (L) | The expected time and compute cost of an agent taking a task. |
| Affinity of a sperm for an egg | Binding Energy | The ranked fit score among willing agents, computed as (c x C_tilde) / L, where C_tilde is capability discounted by the reliability track record. |
| Zona pellucida | Rejection Gate | The pre-execution barrier that admits or deflects an agent before write access. |
| Penetration of the zona | Admission | Passing the gate and gaining write access for a task. |
| Block to polyspermy | Atomic claim | The consistency rule that lets exactly one agent win a task. |
| Cryptic female choice | Decentralised selection | Selection biased by the task signal and agent fitness, with no central assigner. |
| Reactant compatibility (functional groups) | Eligibility filter | The binary check that an agent can act on a task at all: capability domain, permissions, and tools. |
| Activation energy | Firing barrier (Ea) | The minimum Binding Energy a match must reach for the task to proceed. |
| Reaction proceeds | Task fires | An eligible agent clears the barrier and moves to claim and execute the task. |
| Inert (no reaction) | Infeasible or stalled task | No eligible agent (infeasible), or eligible agents that do not clear Ea (stalled). |
| Catalyst | Barrier reducer | Context, a tool, a cache, or a helper agent that lowers the effective Ea for a task. |
| Temperature | Exploration knob | The parameter in the Arrhenius firing extension that sets willingness to try marginal matches. |

## Framework and product terms

These terms have no biological analogue; they name the mechanism and the product layer directly.

| Term | Meaning in the framework |
|------|--------------------------|
| Task wrapper | The orchestrator's envelope around a task. It advertises the task's interface contract (signature, named acceptance criteria, a self-check), which is what a worker receives, and it is also what an agent's compatibility `c` is scored against. The contract for the worker and the compatibility for allocation are two roles of one object (`docs/paper.md` section 5, `docs/measures.md`). |
| Agent wrapper | The calibrated router over a fleet of models. Each model reports a self-assessed confidence (the bid), discounted by its reliability track record `R` on the task type; the task goes to the cheapest model whose corrected bid clears the activation barrier, else escalates to the highest corrected bid, and the winner is screened by the Rejection Gate (`src/cta/wrappers.py`). |
| Reliability track record (R) | The agent's observable history of realised outcomes on a task type, used to discount its self-report. It needs no privileged information and is what makes self-selection robust to miscalibration (H8). |
| Microagent | A small, cheap, specialised worker: a modest model inside a tight harness. The wrappers make a swarm of microagents viable, since the task wrapper supplies the competence a cheap model lacks and the agent wrapper routes to the cheapest capable one. |
| Harness | A model plus its scaffolding, tools, and the wrapped-task envelope that is its contract with the orchestrator. |
| Loop engineering | Designing the outer loop (self-selection, execution, gating, track-record update, annealing) so that calibration and contracts sharpen over rounds; the calibration robustness and cost efficiency are properties of the loop, not of any single call. |
| Token economics | Treating model choice as a portfolio: the activation barrier is price-aware admission control, so cheap-tier tokens clear the tasks a wrapped cheap model can do and premium-tier tokens are reserved for the residual, and the blended cost per task falls as the track record sharpens. |
