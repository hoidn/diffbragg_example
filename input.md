Summary: Align Stage A parity probe and DB-AT-028/029 fixtures onto the same mapping inputs (metadata-sigma smoke dataset) so mapping ROI CC/scale metrics match before chasing the Stage A physics gap.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/

Do Now
- Implement: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result and plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py::main — have both consume mapping_context.inputs (loss_mask/panel_slices/target) from the metadata-sigma smoke dataset (DBEX_SMOKE_* env) and the same HKL/calibration so mapping ROI CC/scale metrics are identical in the probe and fixture; keep mapping metrics persisted even on failure.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/parity_probe --device cuda --sigma-source metadata | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/parity_probe.log; then run pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/pytest_db_at_028_029.log; finally run pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/pytest_db_at_028_029_collect.log.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/{parity_probe/,db_at_028/db_at_028_metrics.json,db_at_029/db_at_029_metrics.json,pytest_db_at_028_029.log,pytest_db_at_028_029_collect.log,summary.md}

How-To Map
1) Export env: `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
2) Update the parity probe and stage_a_smoke_result to pull mapping_context.inputs from the smoke dataset (respect DBEX_SMOKE_*), reuse that same inputs/loss_mask/panel_slices/HKL/calibration in both paths, and log mapping ROI CC/scale metrics before assertions.
3) Run the parity probe command above on CUDA to capture parity_metrics.json under the new artifacts path.
4) Run pytest selectors per Validate (DB-AT-028/029) and then collect-only, teeing logs to the artifacts directory.

Pitfalls To Avoid
- Do not fall back to refined.expt/refined.refl in the probe; honor DBEX_SMOKE_* dataset selection and nearest-neighbor HKL (enable_hkl_interpolation=False).
- Keep mapping ROI metrics persisted even if Stage A still fails; avoid skipping writes on failure.
- Preserve calibration/log_scale_baseline from mapping_context; avoid reinitializing scale or masks outside that context.
- Avoid device drift: probe runs on CUDA for parity with the fixture; keep CPU-only code paths intact but do not change test env defaults.
- No environment changes or new dependencies (Environment Freeze).

If Blocked
- Capture parity_probe.log, parity_metrics.json, db_at_028/db_at_029 metrics, and pytest logs; record mapping ROI CC/scale signatures in docs/fix_plan.md Attempts History and mark TOOLING-VIS-001 blocked on mapping input alignment.

Findings Applied (Mandatory)
- STAGEA-001 — reuse calibrated mapping payload and log mapping metrics before gating; GEOMETRY-003 — keep zero-point tied to mapping baseline and incremental UB parameterization; SCALE-004 — avoid mixing refined assets with metadata smoke datasets.

Pointers
- docs/spec-db-conformance.md:280-366 (DB-AT-028/029 tolerances), dbex/vis/mapping.py:95 (build_mapping_stage_a_context), tests/dbex/test_stage_a_smoke_parity.py:66 (stage_a_smoke_result), plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py.

Next Up (optional)
- If mapping ROI CC aligns but gates still fail, add a small T2 probe to diff target vs model slices for worst ROIs and log in the artifacts dir.

Doc Sync Plan (Conditional)
- Only if DB-AT-028/029 status changes: update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md after tests pass; archive collect-only logs under this loop’s artifacts.

Mapped Tests Guardrail
- Ensure both selectors collect (>0) via the collect-only command before closing the loop; keep logs in the artifacts directory.

Hard Gate
- Do not declare done unless parity_metrics.json and DBAT028/029 metrics exist under `plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/` with mapping_forward_success recorded and mapping ROI CC/scale alignment explained (resolved or blocker captured).

Normative Math/Physics
- Use docs/spec-db-conformance.md:280-366 and docs/spec-db-core.md:84-90 directly for chi²/variance definitions and mapping dataset requirements; do not relax tolerances.
