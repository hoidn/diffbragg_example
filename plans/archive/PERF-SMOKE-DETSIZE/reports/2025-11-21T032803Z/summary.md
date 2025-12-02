### Turn Summary
Relaxed Stage C/B smoke harness config gates so canonical detector strict checks rely on telemetry instead of outdated chi-squared floors.
Documented the telemetry capture workflow in docs/TESTING_GUIDE.md and logged new full-detector runs + metrics in telemetry_full.json / fix_plan.
Next: fix the Stage B `chi_squared_best_b` nonlocal bug so telemetry status becomes “ok” and wire these gates through DB-AT selectors.
Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/ (collect_stage_c_full.log, collect_stage_b_full.log, pytest_stage_c_full.log, pytest_stage_b_full.log, telemetry_full.json)
