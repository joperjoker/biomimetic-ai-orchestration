# Live ACP-broker vignette (real Claude subagents)

A deployed broker routes each prompt by track-record-corrected confidence,
forwards the turn to the chosen real model, and records the outcome. The
track record is warm-started from the capability-ladder calibration.

| turn | task | routed to | corrected bids (h/s/o) | outcome |
|------|------|-----------|------------------------|---------|
| 1 | `fraction_to_decimal` | **haiku** | 0.85/0.92/0.96 | pass |
| 2 | `multiply_strings` | **haiku** | 0.85/0.92/0.96 | pass |
| 3 | `word_break` | **haiku** | 0.85/0.92/0.96 | pass |
| 4 | `is_match` | **sonnet** | 0.59/0.92/0.96 | pass |

- Routed spend: $0.04500 for the 4 turns; always-frontier would cost $0.72000: a **16.0x** saving.
- The barrier is 0.70. Every task whose cheapest corrected bid clears it routes
  cheap; `is_match` (Haiku reliability 0.70, corrected bid below the barrier)
  escalates, protecting completion exactly where the cheap model is unreliable.
