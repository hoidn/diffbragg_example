Summary: Enforce the apply_calibration_n_cells gate throughout the Stage A engine stack so metadata-small smoke runs no longer reintroduce oversampled N_cells after mapping suppresses them.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity, tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T172416Z/
Do Now:
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_lbfgs_closure — propagate RefinementConfig.apply_calibration_n_cells through every create_crystal_config retarget (LBFGS warm cache, _build_final_bragg_from_stage_a_telemetry, Stage B eval/cold fallbacks) and extend _build_final_bragg_from_stage_a_telemetry to emit n_cells_applied + suppression_reason so Stage A telemetry proves the gate state matches mapping.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T172416Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T172416Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
How-To Map:
1. mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-25T172416Z/{db_at_028,db_at_029}.
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T172416Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T172416Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T172416Z/pytest_db_at_028_029_collect.log.
3. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T172416Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T172416Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T172416Z/pytest_db_at_028_029.log.
Pitfalls To Avoid:
- Do not re-enable N_cells for detector-size modes that still rely on SCALE-005 (full detector / DB-AT-024); the gate must stay opt-in via config.
- Keep calibration metadata immutable on disk—clone dicts before tagging telemetry or adjusting spot_scale_override.
- Ensure every create_crystal_config call respects config.apply_calibration_n_cells, including Stage B CPU fallbacks and Stage C prep.
- When adding telemetry fields, update both inline and engine delegation paths so DB-AT selectors see the same schema.
- Preserve device/dtype neutrality when tensorizing masks or HKL grids; no CUDA-only shortcuts.
- Leave Stage A log-scale baseline math untouched except where the gate affects simulator scale factors.
- Avoid touching external dependencies or installing packages (Environment Freeze remains in effect).
If Blocked:
- If simulators still reintroduce N_cells, capture the updated db_at_028/db_at_029 metrics + mapping_context_fixture JSONs plus stderr logs under the artifacts path and note the mismatch in docs/fix_plan.md Attempts History before pausing.
Findings Applied (Mandatory):
- STAGEA-001 — Mapping calibration/telemetry is authoritative; Stage A changes must keep telemetry in sync.
- SCALE-008 — When mapping suppresses N_cells and adjusts spot_scale, Stage A must honor the same gate and baseline without double-applying the correction.
Pointers:
- docs/data_dependency_manifest.md:84 — Small-detector smoke calibration/MTZ defaults and provenance that define the expected inputs for these selectors.
- docs/spec-db-conformance.md:280 — DB-AT-028/029 chi² and ROI correlation requirements we continue to measure.
- plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/db_at_029/mapping_context_fixture.json:25 — Mapping telemetry showing n_cells_applied=false + positive ROI CC.
- plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/db_at_029/db_at_029_metrics.json:2 — Stage A telemetry still recording negative ROI CC under the same run.
- dbex/nanobrag_refinement.py:1862 — LBFGS warm-cache retarget path currently calls create_crystal_config with apply_n_cells hard-coded to True when N_cells exists.
- dbex/nanobrag_refinement.py:2740 — _build_final_bragg_from_stage_a_telemetry recreates simulators with apply_n_cells=(N_cells is not None), undoing the gate.
Next Up (optional):
- If Stage A telemetry and mapping finally agree on the gate, rerun plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py to document ROI CC parity across calibration variants.
