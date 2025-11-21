### Turn Summary
Enforced the nanobrag CLI sigma_readout guard and plumbed sigma provenance/value through RefinementConfig, per-stage telemetry, and `/torch_diagnostics` so spec-db-core.md:32-68 stays satisfied.
Added the sigma guard regression plus telemetry assertions in `tests/dbex/test_refine_one_cli.py` and documented the operator workflow in `docs/TESTING_GUIDE.md`/`docs/development/TEST_SUITE_INDEX.md`.
Next: expose calibrated sigma maps from `DataLoad` so the guard can consume instrument metadata instead of requiring `--sigma-rdout`.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T054520Z/ (pytest_cli_sigma.log, collect_cli_sigma.log)

### Turn Summary
Marked PHYSICS-LOSS-001 Phase C checklists complete in `plans/active/PHYSICS-LOSS-001/implementation.md:42-45` and tied them back to the 2025-11-21T052443Z Stage A/DB-AT evidence.
Updated `docs/fix_plan.md:15-34` and `galph_memory.md:297-304` to capture the sigma-provenance gap plus the fresh report directory.
Replaced `input.md:1-65` with a ready-for-implementation Do Now covering the CLI sigma guard, telemetry provenance fields, doc sync, and pytest selectors.
Next: implement the sigma_readout fail-fast path, emit the provenance telemetry, update docs/tests, and record the CLI pytest log in the new report directory.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T054520Z/ (summary.md)
