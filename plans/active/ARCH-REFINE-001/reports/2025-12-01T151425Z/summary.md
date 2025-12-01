### Turn Summary
Implemented Stage B baseline parity guard so CLI diagnostics always compare Stage B initial chi² against Stage A canonical baseline; telemetry now includes stage_b_baseline_rel_diff/abs_diff/diff_path fields.
Resolved the REFINE-FLOW-001 baseline drift detection by adding explicit float comparison and JSON diff emission when relative difference exceeds 0.1% tolerance; both Stage B/C small-detector smokes pass.
Next: run the full Stage B/C smoke module and refresh architecture docs only if telemetry schema changed (parity fields are custom, no schema impact).
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T151425Z/ (pytest_stage_bc_small_v2.log, telemetry_stage_bc_small.json)
