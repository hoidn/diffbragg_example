### Turn Summary
Enforced the Stage-smoke detector guard by sharing the resolver in tests/conftest.py and syncing docs/test registries so DB-AT selectors now hard-require --smoke-detector-size=full.
Recorded collect-only evidence, a deliberate guard failure, Stage A/B/C full-detector smokes (A pass, B/C below improvement gates), and a passing DB_AT_021 run; logs live alongside the initiative artifacts.
Problems remain: Stage B improvement = -7.6e-8% and Stage C improvement = 0% fail the calibrated parity gates on the canonical detector, so exit criterion #4 cannot close yet.
Next: debug or recalibrate the Stage B/C full-detector gates while preserving the new guard, then re-run the full smoke suite for updated telemetry.
Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/ (collect_stage_a_full.log, pytest_stage_smokes_full.log, pytest_db_at_021_small_guard.log, pytest_db_at_021_full.log)

### Turn Summary
Documented the DB-AT detector guard gap and rewrote the PERF-SMOKE-DETSIZE handoff (fix plan + input.md) so the next loop focuses on hardening pytest before parity resumes.
Called for a pytest-level UsageError when DB_AT tests run with the cropped detector and outlined the telemetry capture needed after rerunning Stage A/B/C smokes and DB_AT_021 on the full footprint.
Next: Ralph implements the guard/doc updates and records the Stage smoke + DB-AT logs (plus an optional guard-failure run) under the new artifacts directory.
Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/ (pytest_stage_smokes_full.log, pytest_db_at_021_full.log, optional pytest_db_at_021_small_guard.log)
