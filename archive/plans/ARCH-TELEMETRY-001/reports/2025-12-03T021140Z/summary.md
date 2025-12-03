### Turn Summary
Removed `to_legacy_dict()` calls from Stage B and Stage C production code; both stages now access telemetry/perf counters directly via typed dataclass fields.
test_stage_b_baseline_guard_diff_payload PASSED (validates direct field access); two smoke tests SKIPPED due to missing sigma_readout_map fixture (expected environmental limitation, not code regression).
Next: Phase C.4 to remove RefinementEngine key mapping in engine.py.
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T021140Z/ (pytest_phase_c32.log)
