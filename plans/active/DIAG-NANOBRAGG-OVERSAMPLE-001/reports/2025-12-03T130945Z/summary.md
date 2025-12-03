### Turn Summary
Scoped Phase D around a Tier-2 trace script so the unit-mismatch evidence moves from ad-hoc logs to a reproducible probe with parsed metrics.
Captured the script contract plus canonical command in phase_d_trace_plan.md and rewrote input.md so Ralph implements the tool and refreshes DIAG-UNIT-001 next loop.
Next: build/run trace_simulator_mismatch.py against the smoke fixtures, update the finding with the new artifact path, and rerun the config factory pytest guard.
Artifacts: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/ (phase_d_trace_plan.md)

_2025-12-08 note_: DIAG-UNIT-001 has been reclassified as **Retracted** after reviewing the production `_compute_physics_for_position` path; the trace hook was mixing units when recomputing `hkl_frac`. Phase E now tracks actual HKL coverage stats instead of chasing a non-existent unit mismatch.
