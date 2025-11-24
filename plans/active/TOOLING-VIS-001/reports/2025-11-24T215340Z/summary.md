### Turn Summary
Planned the Phase D.B zero-point probe plus DB-AT-027 xfail selector so Stage A mapping invariants are guarded before calibration plumbing.
Captured the Phase D.A telemetry deltas (scale mismatch, chi² explosion), logged finding STAGEA-001, updated docs/fix_plan.md, and rewrote input.md with the new ready_for_implementation runbook.
Next: implement `run_engine_zero_point_probe`, wire the plan-local CLI/test, run the helper to produce stage_a_engine_zero_point.json, and register the selector in the testing docs.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T215340Z/ (zero_point_probe_plan.md, input.md)
