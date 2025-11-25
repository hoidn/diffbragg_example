Summary: Propagate the apply_calibration_n_cells gate through the Stage A engine path so the warm cache, reconstruction helper, and CLI config honor the same calibration choice as the mapping context.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity, tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/
Do Now:
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_context — thread apply_calibration_n_cells through RefinementConfig, Stage A context/reconstruction, and the nanobrag CLI/tests so the engine skips N_cells whenever the mapping context (and dataload) suppresses them.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
How-To Map:
1. mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/{db_at_028,db_at_029}.
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/pytest_db_at_028_029_collect.log.
3. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/pytest_db_at_028_029.log.
Pitfalls To Avoid:
- Do not re-enable N_cells for full-detector or DB-AT-024 contexts; gate only when the dataload/mapping context requests it.
- Keep the calibration dict immutable on disk—clone when tagging `calibration_adjusted_for_n_cells`.
- Preserve telemetry fields (`log_scale_baseline_source`, adjustment factor, masked means) while refactoring helper signatures.
- Ensure Stage B CPU fallbacks and `_build_final_bragg_from_stage_a_telemetry` reuse the same gate so reconstruction matches live refinement.
- Maintain device/dtype neutrality when tensorizing masks or HKL grids; no CUDA-only shortcuts.
- Environment freeze: no pip installs or module upgrades while touching CLI/test plumbing.
If Blocked:
- If Stage A still reports `n_cells_applied=true`, capture the mapping vs Stage A telemetry JSONs plus stderr in plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/, note the mismatch in docs/fix_plan.md Attempts History, and pause for supervisor guidance.
Findings Applied:
- POLICY-001 — Environment freeze stays in effect; code-only edits with artifacts logged.
- STAGEA-001 — Mapping calibration is canonical; propagate its gating/telemetry without regression.
- SCALE-008 — Stage A must reuse mapping-aware log-scale baselines and suppress N_cells when diagnostics demand it.
Pointers:
- docs/spec-db-conformance.md:280 — DB-AT-028/029 chi² and ROI correlation gates that remain authoritative even when we expect failures.
- docs/data_dependency_manifest.md:90 — Small-detector smoke bundle & calibration assets that define the intended inputs for these selectors.
- docs/findings.md:41 — SCALE-008 description of the mapping-aware log-scale baseline requirements.
- dbex/nanobrag_refinement.py:739 — `_build_stage_a_context` hot path that currently always applies N_cells; extend it with the new gate.
Next Up:
- After the gate propagates, rerun plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py for the metadata_calibrated_drop_ncells case to prove Stage A + mapping now agree on ROI correlations.
