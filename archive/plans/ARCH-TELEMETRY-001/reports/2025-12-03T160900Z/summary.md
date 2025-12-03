### Turn Summary
Extended StageBTelemetryCollector with set_baseline_parity_metrics helper; updated _check_stage_b_baseline_parity and Stage C closures to route telemetry through collectors instead of direct state mutation; added missing Optional import.
test_stage_b_baseline_guard_diff_payload PASSED; test_stage_b_shell_modifiers FAILED with "'StageBTelemetryCollector' object does not support item assignment" during optimization (4 validations, 0 closure evals). Root cause likely: collector passed to code expecting dict/dataclass subscriptable object.
Next: Debug __setitem__ error by tracing where collector is treated as dict (likely in closure/param construction); investigate if param_values threading accidentally passes collector where telemetry_state expected.
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T160900Z/ (pytest_stage_b_guard.log PASSED, pytest_stage_b_smoke.log FAILED)
