Summary: Align Stage A parity probe and DB-AT-028/029 fixtures to use the same mapping dataset/HKL/calibration so mapping ROI CC/scale metrics are consistent and gates can tighten.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/

Do Now
- Implement: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result and plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py::main — refactor both to build the mapping forward stack via build_mapping_stage_a_context (metadata sigma dataset, nearest-neighbor HKL) and share the same hkl_indices/hkl_source/hkl_path + calibration/loss_mask/inputs so the parity probe and pytest fixture use an identical dataset/device; persist mapping ROI CC and scale metrics before assertions even if Stage A refinement fails.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/parity_probe --device cpu --sigma-source metadata | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/parity_probe.log; then run pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/pytest_db_at_028_029.log; finally run pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/pytest_db_at_028_029_collect.log.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/{parity_probe/,db_at_028/db_at_028_metrics.json,db_at_029/db_at_029_metrics.json,pytest_db_at_028_029.log,pytest_db_at_028_029_collect.log,summary.md}

How-To Map
1) Export env: `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
2) Update both the parity probe and stage_a_smoke_result to construct mapping inputs via build_mapping_stage_a_context (use the metadata sigma dataset + nearest-neighbor HKL, propagate hkl_path/source, calibration, and loss_mask/inputs); ensure mapping ROI CC/scale metrics are logged before assertions and that the fixture no longer diverges by device or dataset.
3) Run the parity probe command above (CPU) to capture parity_metrics.json under the new artifacts path.
4) Run pytest selectors per Validate (DB-AT-028/029) and then collect-only, teeing logs to the artifacts directory.

Pitfalls To Avoid
- Keep enable_hkl_interpolation=False for DB-AT-028/029; do not reintroduce refined HKL swaps or log_scale_baseline drift.
- Use the same mapping dataset/calibration for probe and fixture (metadata sigma dataset); avoid mixing refined.expt with metadata refGeom.
- Preserve mapping ROI metrics even on failure; do not short-circuit artifact writes.
- Respect device neutrality: probe may run on CPU but ensure fixture can reuse the same mapping HKL/calibration without GPU-only assumptions.
- No environment changes or new dependencies (Environment Freeze).

If Blocked
- Capture parity_probe.log, parity_metrics.json, db_at_028/db_at_029 metrics, and pytest logs; note mapping ROI CC/scale signatures in docs/fix_plan.md Attempts History and mark TOOLING-VIS-001 blocked pending dataset/HKL alignment.

Findings Applied (Mandatory)
- STAGEA-001 — reuse calibrated mapping payload (spot_scale/log_scale_baseline) and log mapping metrics before gating.

Pointers
- docs/spec-db-conformance.md:280-366 (DB-AT-028/029 tolerances and mapping dataset rules), plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py, tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result.

Next Up (optional)
- If mapping ROI CC aligns after dataset/HKL unification but gates still fail, add a small T2 probe to diff target/model slices for the worst ROI.

Doc Sync Plan (Conditional)
- If DB-AT-028/029 status changes, update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md after tests pass; archive collect-only logs under this loop’s artifacts.

Mapped Tests Guardrail
- Ensure both selectors collect (>0) via the collect-only command before closing the loop; keep logs in the artifacts directory.

Hard Gate
- Do not declare done unless parity_metrics.json plus DBAT028/029 metrics exist under `plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/` with mapping_forward_success recorded (even on failure signatures) and the mapping ROI CC/scale values reconciled between probe and fixture or clearly logged as the blocker.

Normative Math/Physics
- Use docs/spec-db-conformance.md:280-366 and docs/spec-db-core.md:84-90 directly for chi²/variance definitions and mapping dataset requirements; do not relax tolerances.
