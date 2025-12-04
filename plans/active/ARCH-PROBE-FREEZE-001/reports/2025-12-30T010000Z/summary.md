### Turn Summary — 2025-12-30T010000Z (Supervisor)

- Confirmed Phase B.3/B.4 outputs are green: DB-AT-028/029 now emit Stage A baseline metrics via owner telemetry, and sigma metadata embedding lives in `dbex.tools.embed_sigma_external_lookup` with the legacy plan script reduced to a shim.
- Selected `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py` (671 LOC shadow pipeline) as Phase B.5 target. Planned to create `dbex/calibration/config_variants.py` + `dbex/tools/mapping_dataset_metrics.py`, shrink the plan script into a legacy wrapper, and update docs/tests so operators call the canonical CLI.
- Reserved this report directory for the upcoming implementation artifacts: CLI command log, `mapping_dataset_metrics.json`, ROI diagnostics, pytest logs, and documentation diffs.
- Findings referenced: diagnostic_script_policy (prompts/supervisor.md §10), STAGEA-001, SCALE-004/005, DATA_DEPENDENCY_MANIFEST. Problems ledger directive "Freeze plan-local probe scripts…" remains open; this loop services it by targeting the largest remaining shadow pipeline.
- Next loop is implementation_ready: build the new modules, update docs/plan notes, run the CLI for `metadata_raw` + `metadata_calibrated` under `DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small`, and deposit artifacts here. Forbidden: no new plan-local probe scripts.

### Turn Summary — 2025-12-30T010000Z (Ralph Implementation)

Migrated mapping dataset metrics probe (670+ LOC) into production owner modules, reducing plan script to 39-line shim.
Created `dbex/calibration/config_variants.py` (materialize_calibration_variant, resolve_dataset_paths/hkl/calib helpers) and `dbex/tools/mapping_dataset_metrics.py` (CLI + importable runner).
Validation: both metadata cases (raw/calibrated) ran successfully with ROI artifacts emitted (32 PNG/NPZ pairs); DB-AT-028/029 selectors collected (2 tests).
Artifacts: `mapping_dataset_metrics.json`, `probe.log`, ROI diagnostics under `mapping_dataset_metrics/`, `collect_db_at_028_029.log`, tools README updated.
