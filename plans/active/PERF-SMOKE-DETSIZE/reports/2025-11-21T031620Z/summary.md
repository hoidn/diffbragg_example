### Turn Summary
Documented the DB-AT detector guard gap and rewrote the PERF-SMOKE-DETSIZE handoff (fix plan + input.md) so the next loop focuses on hardening pytest before parity resumes.
Called for a pytest-level UsageError when DB_AT tests run with the cropped detector and outlined the telemetry capture needed after rerunning Stage A/B/C smokes and DB_AT_021 on the full footprint.
Next: Ralph implements the guard/doc updates and records the Stage smoke + DB-AT logs (plus an optional guard-failure run) under the new artifacts directory.
Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/ (pytest_stage_smokes_full.log, pytest_db_at_021_full.log, optional pytest_db_at_021_small_guard.log)
