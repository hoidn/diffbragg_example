Summary: Capture mapping_context diagnostics to reconcile parity probe vs DB-AT-028/029 mapping metrics before adjusting Stage A physics.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py::main and tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result — persist mapping_context diagnostics (dataset paths, sigma provenance, HKL source/path, target/Bragg stats, ROI CC/scale ratios, device) to artifacts via a shared helper so the probe and pytest fixture log identical mapping metrics even on failure.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/parity_probe --device cuda --sigma-source metadata | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/parity_probe.log; then run pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/pytest_db_at_028_029.log; finally run pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/pytest_db_at_028_029_collect.log.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/{parity_probe/parity_metrics.json,parity_probe/mapping_context_probe.json,parity_probe.log,db_at_028/db_at_028_metrics.json,db_at_029/db_at_029_metrics.json,db_at_028/mapping_context_fixture.json,db_at_029/mapping_context_fixture.json,pytest_db_at_028_029.log,pytest_db_at_028_029_collect.log,summary.md}

How-To Map
1) Export env: `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
2) In the probe + fixture, add a shared helper to emit mapping_context diagnostics (dataset paths, sigma map presence, hkl_source/path, target/loss_mask stats, ROI CC/scale ratios, scale hints, device) into JSON under the artifacts path before assertions so failures still capture context.
3) Run the parity probe command above on CUDA; verify both `parity_metrics.json` and `mapping_context_probe.json` exist under `parity_probe/`.
4) Run pytest command for DB-AT-028/029 (same env) so `db_at_028_metrics.json`, `db_at_029_metrics.json`, and mapping_context_fixture diagnostics are written; then run the collect-only command to confirm selectors register (>0) and archive logs.
5) If mapping metrics still diverge, note probe vs fixture deltas (ROI CC, scale_ratio, target means) in summary.md for follow-up.

Pitfalls To Avoid
- Do not change dataset selection logic: keep metadata sigma + nearest-neighbor HKL; no refined.mtz overrides or calibration swaps.
- Persist diagnostics before assertions so artifacts exist even when gates fail.
- Avoid mutating mapping_context inputs between probe and fixture; reuse the same helper/structure for metrics.
- Keep device/dtype consistent (CUDA float32) and honor loss_mask from mapping_context without reindexing.
- No environment changes or new dependencies (Environment Freeze).
- Do not relax DB-AT-028/029 tolerances; log discrepancies instead.

If Blocked
- Capture parity_probe.log, parity_metrics.json, mapping_context_* diagnostics, db_at_028/db_at_029 metrics, and pytest logs; record the divergence signatures in docs/fix_plan.md Attempts History and mark TOOLING-VIS-001 blocked on mapping diagnostics alignment.

Findings Applied (Mandatory)
- STAGEA-001 — Reuse calibrated mapping payload and log mapping metrics before gating; document parity probes in artifacts.
- GEOMETRY-003 — Keep zero-point tied to mapping baseline and incremental UB parameterization; avoid refined overrides.

Pointers
- docs/spec-db-conformance.md:280-366 (DB-AT-028/029 tolerances)
- dbex/vis/mapping.py:95 (build_mapping_stage_a_context inputs + diagnostics)
- tests/conftest.py:30 (smoke dataset resolution for metadata/full)
- tests/dbex/test_stage_a_smoke_parity.py:66 (stage_a_smoke_result fixture)
- plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py

Next Up (optional)
- If mapping metrics align but ROI CC remains low, diff worst-ROI slices between mapping and Stage A in a T2 probe under this initiative path.

Doc Sync Plan (Conditional)
- Only if DB-AT-028/029 status changes: update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md after tests pass; archive collect-only logs under this loop’s artifacts.

Mapped Tests Guardrail
- Keep the collect-only command in Artifacts; ensure both selectors collect (>0) before closing the loop.

Hard Gate
- Do not declare done unless both mapping_context diagnostics (probe + fixture) and DBAT028/029 metrics exist under the artifacts path with mapping_forward_success recorded or the blocking delta explained in summary.md.

Normative Math/Physics
- Use docs/spec-db-conformance.md §280-366 and docs/spec-db-core.md §84-90 directly for chi²/variance/ROI CC definitions; do not paraphrase or relax tolerances.
