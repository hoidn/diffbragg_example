### Turn Summary
Reviewed the 2025-11-26T003000Z Stage A log-scale override attempt and confirmed telemetry still reports a null baseline source while `scale_ratio_before≈2.0e4` (`plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/db_at_029/db_at_029_metrics.json`).
Captured the failure analysis in docs/fix_plan.md and rewrote input.md with a Do Now that propagates calibration adjustment flags into Stage A and updates `_build_stage_a_params`/fixtures to consume the mapping `global_scale_hint` baseline.
Next: Ralph implements the plan and reruns DB-AT-028/029 so artifacts prove Stage A zero-iteration intensities now match the mapping stack.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T010900Z/ (input.md, planning notes)
