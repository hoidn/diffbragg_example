### Turn Summary
Implemented writer/artifact plumbing so Stage B baseline metrics are sourced from engine artifacts instead of telemetry shims; HDF5 schema remains byte-for-byte compatible.
All artifact plumbing changes complete and tested (CLI writer test PASSED, Stage C small PASSED); Stage B shell test revealed pre-existing dict-compat bug in StageBTelemetryState that blocks execution (unrelated to artifact work).
Next: investigate and fix StageBTelemetryState item assignment bug, then re-validate Stage B smoke tests with artifact-sourced baseline metrics.
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T110000Z/ (pytest_cli_writer.log, pytest_stage_c_small.log, pytest_stage_b_shell.log)
