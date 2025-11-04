Summary: Sync DB_AT_024 documentation, findings, and artifacts with the passing sample-clipping fix while keeping Phase D3 accountable.
Mode: Parity
Focus: MAP-SCALE-001 — Zero-iteration mapping scale alignment
Branch: integration
Mapped tests: tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z/{collect_db_at_024.log,pytest.log,mapping_metrics.json,mapping_metrics.csv,summary.md}
Do Now:
- MAP-SCALE-001:
  - Implement: `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` (refresh docstring/comments to state thresholds now pass and capture the new metrics) and update `docs/TESTING_GUIDE.md` §2 plus `docs/development/TEST_SUITE_INDEX.md` DB_AT_024 entries with the 2025-11-04T190041Z metrics; revise `docs/findings.md` (SCALE-005) to note the guard now triggers when beam metadata is forwarded.
  - Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1`
  - Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z/
How-To Map:
1. `mkdir -p plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke | tee plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z/collect_db_at_024.log`
3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z/pytest.log`
4. `jq '{corr_median, localization_success_rate, calibration: {n_cells_applied}}' plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z/mapping_metrics.json`
Pitfalls To Avoid:
- Do not reintroduce `xfail`/skip logic or weaken the DB_AT_024 assertions now that thresholds pass.
- Preserve `diagnostics['n_cells_applied']` and calibration fields when editing the test docstring/comments.
- Keep documentation metrics sourced from the latest artifacts (2025-11-04T190041Z) to avoid drift with stale baselines.
- Maintain Environment Freeze: no package installs or simulator rebuilds.
- When editing findings, keep SCALE-005 warning about missing beam metadata—only add the conditional success note.
- Ensure `DBAT024_ARTIFACT_DIR` points to the fresh timestamp before running pytest so artifacts land in the correct folder.
If Blocked: Capture the failing command output, store it under `plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z/`, update `docs/fix_plan.md` Attempts History with the error signature, and notify Galph before altering additional files.
Findings Applied (Mandatory):
- SCALE-002 — Guard single application of √spot_scale; confirm documentation stresses post-sim scaling only.
- SCALE-003 — Reference calibrated √spot_scale and refined |F| expectations when updating docs/test comments.
- SCALE-004 — Document refined geometry dependency in the refreshed notes to keep parity expectations accurate.
- SCALE-005 — Clarify that forwarding `beam_config` alongside `N_cells` resolves the intensity blow-up while retaining the beam metadata guard.
Pointers:
- docs/spec-db-conformance.md:43-46 — Acceptance thresholds for DB_AT_024.
- docs/TESTING_GUIDE.md:61-84 — Selector table row to update with new metrics/artifacts.
- docs/development/TEST_SUITE_INDEX.md:21-33 — Registry entry requiring status/metric refresh.
- docs/findings.md:17-19 — SCALE-003/SCALE-005 narratives to align with the implemented fix.
- docs/config_crosswalk.md:37-72 — Beam/crystal metadata mapping that underpins the documentation edits.
- docs/nanobrag_api.md:30-68 — Sample clipping semantics referenced in the findings/doc updates.
- plans/active/MAP-SCALE-001/implementation.md:35-38 — Phase D3 checklist item governing this loop.
Next Up (optional): 1. Evaluate DB_AT_024 artifacts for photon-mode inputs once doc sync is complete.
