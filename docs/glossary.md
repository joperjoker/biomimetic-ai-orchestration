# Glossary: Biology to Engineering Mapping

This glossary maps the biological vocabulary of cryptic female choice onto the engineering concepts of the framework. It is the quick reference for readers who meet a biological term and want its computational meaning.

| Biological term | Engineering concept | Meaning in the framework |
|-----------------|---------------------|--------------------------|
| Egg | Task | The unit of work that advertises itself and is selected for. |
| Chemical signal (chemoattractant) | Scent envelope | The semantic metadata a task emits to attract suitable agents. |
| Sperm | Agent | A distributed worker that approaches tasks and competes for them. |
| Chemotaxis (attraction strength) | Task Signal (S) | How strongly a task envelope matches an agent domain. |
| Gamete fitness | Agent Capability (C) | The agent competence for the required skills. |
| Energetic cost of approach | Latency penalty (L) | The expected time and compute cost of an agent taking a task. |
| Affinity of a sperm for an egg | Binding Energy | The ranked fit score, computed as (S x C) / L. |
| Zona pellucida | Rejection Gate | The pre-execution barrier that admits or deflects an agent before write access. |
| Penetration of the zona | Admission | Passing the gate and gaining write access for a task. |
| Block to polyspermy | Atomic claim | The consistency rule that lets exactly one agent win a task. |
| Cryptic female choice | Decentralised selection | Selection biased by the task signal and agent fitness, with no central assigner. |
