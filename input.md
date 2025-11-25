Summary: Gate DiffBragg N_cells for the metadata small-detector fixtures while preserving telemetry so we can undo the Stage-A anti-correlation introduced by oversampled calibration payloads.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T220500Z/

Do Now:
- Implement: dbex/nanobrag_bridge.py::simulate_forward_once + dbex/vis/mapping.py::build_mapping_stage_a_context + tests/conftest.py::refgeom_dataload — add an apply_calibration_n_cells flag (default True) that the Stage-A smoke fixture and TOOLING probes can set to False for the refGeom_small metadata dataset, propagating the setting through compare_mapping_dataset_metrics.py::build_dataload_for_case and compare_mapping_forward_cpu_gpu.py::Args.__init__ so mapping contexts record when N_cells is suppressed.
- Validate: `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` under the canonical metadata env so both selectors archive mapping_context telemetry showing n_cells_applied changes (failures on chi²/ROI gates remain acceptable).

How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T220500Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` and `mkdir -p "$REPORT"/{mapping_dataset_metrics,db_at_028,db_at_029}`.
2. After extending the probe, run `python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py --cases metadata_raw metadata_calibrated metadata_calibrated_drop_ncells metadata_calibrated_spot1_drop_ncells --emit-roi-artifacts --roi-count 16 --default-sigma 3.0 --device cuda:0 --out-dir "$REPORT"/mapping_dataset_metrics | tee "$REPORT"/mapping_dataset_metrics/probe.log`; confirm stdout logs each derived calibration path plus whether N_cells was removed.
3. Export DB-AT artifact dirs: `export DBAT028_ARTIFACT_DIR="$REPORT"/db_at_028 DBAT029_ARTIFACT_DIR="$REPORT"/db_at_029`, run `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029_collect.log`, then run the validating command above and tee to `$REPORT`/pytest_db_at_028_029.log (failures are expected; ensure mapping_context_fixture.json reflects n_cells gating).

Pitfalls To Avoid:
- Keep the new flag defaulting to True so DB-AT-024/full-detector paths stay untouched.
- Do not mutate captured calibration configs; materialize drop_ncells variants inside the report directory only.
- Continue to resolve HKL and sigma assets via the manifest precedence; never bypass explicit env overrides.
- Make sure diagnostics record whether n_cells_applied was forced False plus the reason, otherwise telemetry loses auditability.
- Preserve lazy import patterns inside simulate_forward_once/build_mapping_stage_a_context; no top-level nanobrag_torch imports.
- Mapping probes/tests must rerun after code changes; stale JSON makes it impossible to prove the gating worked.

If Blocked:
- If simulate_forward_once refusals or calibration parsing errors appear, capture the traceback in `$REPORT/mapping_dataset_metrics/probe.log`, halt immediately, and record the blocker in docs/fix_plan.md + summary.md before attempting retries.
- If pytest selectors stop collecting, save both log files, mark TOOLING-VIS-001 blocked with the new failure signature, and avoid partial code reverts.

Findings Applied (Mandatory):
- STAGEA-001 — smoke tooling must share calibration/HKL provenance with Stage A; the new flag simply controls how that calibration is consumed.
- SCALE-004 — refined MTZ + calibration metadata stay paired even when N_cells is suppressed; no raw HKL fallbacks.
- SCALE-005 — changes to N_cells wiring must remain auditable with explicit telemetry so future initiatives know when sample clipping is active.

Pointers:
- docs/data_dependency_manifest.md:34-120 — canonical smoke asset precedence and detector-size overrides that the new flag must honor.
- docs/architecture/calibration_scaling.md:1-120 — explains how spot_scale/N_cells/beam metadata should influence simulate_forward_once.
- docs/spec-db-conformance.md:204-366 — DB-AT-028/029 requirements this gating aims to unblock.
- plans/active/TOOLING-VIS-001/implementation.md:190-320 — Phase D objectives and acceptance gates for mapping/Stage-A parity.

Next Up (optional):
- If N_cells gating stabilizes ROI CC, plan a follow-up loop to revisit the calibration capture workflow so small-detector bundles export a “sample-clip safe” flag instead of hard-coded suppression.
