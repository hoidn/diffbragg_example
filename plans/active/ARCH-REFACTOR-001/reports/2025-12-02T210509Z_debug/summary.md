### Turn Summary
Fixed RefinementEngine telemetry key mapping to return legacy "A"/"B"/"C" labels instead of "stage_a"/"stage_b"/"stage_c" for backward compatibility with test suite.
Primary issue resolved: 3/5 smoke tests now PASSED (test_stage_a_expansion, test_stage_b_shell_modifiers, test_stage_c_detector_microslip); telemetry key mismatch eliminated.
Remaining 2/5 test failures are secondary bugs unrelated to key mapping: test_stage_a_engine_delegation_telemetry needs engine_protocol field population (Phase E feature), test_stage_b_per_reflection_smoke needs Stage A artifacts storage fix.
Next: Escalate 2 remaining failures to Galph for triage as separate harness/spec_change initiatives; Phase D.3 Batch 1 can proceed now that telemetry keys are compatible.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210509Z_debug/ (pytest_smoke_tests_fixed.log, test_results_summary.md)
