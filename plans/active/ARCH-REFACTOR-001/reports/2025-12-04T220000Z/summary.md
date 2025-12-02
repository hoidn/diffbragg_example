### Turn Summary
Fixed 2 Engine bugs (artifacts storage + Phase E telemetry) blocking Phase D.3 test migration; both target bugfixes validated successfully.
Bug #1: StageAArtifacts now created unconditionally (cold mode supported), Bug #2: engine_protocol and stage_modes fields now populated via new helper methods.
Next: Resume Phase D.3 test migration with all 5 smoke tests (should now be 5/5 PASSED); Stage B ASU gradient flow issue is separate concern requiring investigation.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-04T220000Z/ (pytest_engine_bugfixes.log, test_results_summary.md)
