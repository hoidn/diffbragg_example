# galph_memory.md — Supervisor Turn Log (DBEX)

Use this file to append a single line per supervisor turn capturing the FSM state and dwell count for the current focus.

Template (copy/paste and fill values each turn):
```
[timestamp] focus=<id/slug> state=<gathering_evidence|planning|ready_for_implementation> dwell=<n> artifacts=plans/active/<initiative>/reports/<YYYY-MM-DDTHHMMSSZ>/ next_action=<one-liner or 'switch_focus'>
```

Example:
```
2025-10-28T12:34:56Z focus=TORCH-BRIDGE-001 state=gathering_evidence dwell=1 artifacts=plans/active/TORCH-BRIDGE-001/reports/2025-10-28T123456Z/ next_action=map parity selector and artifact hub
```

Notes
- Enforce the dwell guard: on the 3rd consecutive turn in `gathering_evidence` or `planning` for the same focus, either transition to `ready_for_implementation` with a concrete Do Now or switch focus and record the block in `docs/fix_plan.md`.
- See `prompts/fsm_analysis.md` for the canonical state list and transitions.
