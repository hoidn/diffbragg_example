### Turn Summary
Implemented REFINE-014 by extracting Stage A's raw pre-tanh orientation_vec from telemetry and passing it through frozen params, eliminating the double-tanh collapse hypothesis.
Both detector sizes achieved 99.999994% offset reduction, but chi² still regressed by ~0.065% (identical to pre-fix), disproving the REFINE-014 hypothesis and triggering the repeat-failure guard.
Per ground_rules, marked PERF-WARM-SIM-001 blocked pending supervisor investigation of Stage C loss computation path, frozen parameter handling, or Stage A/C chi² initialization alignment.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/ (pytest_stage_c_small.log, pytest_stage_c_full.log, telemetry_stage_c_small.json, telemetry_stage_c_full.json, stage_c_warm_cache_report.json, collect logs)
