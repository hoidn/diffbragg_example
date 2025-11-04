Summary: Surface refined structure-factor telemetry in the zero-iteration helper and guard DB_AT_024 with assertions.
Mode: none
Focus: MAP-SCALE-004 — Zero-iteration telemetry parity
Branch: integration
Mapped tests:
- pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
- pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz --maxfail=1 -q
Artifacts: plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/
Do Now:
- MAP-SCALE-004: Implement: dbex/nanobrag_bridge.py::simulate_forward_once + tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping.test_db_at_024_mapping_smoke — surface structure-factor telemetry (hkl_source/count/mean/path) in zero-iteration diagnostics and harden DB_AT_024 assertions while keeping CLI telemetry unchanged. Validate: pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1; pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz --maxfail=1 -q.
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke | tee plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/collect_db_at_024.log
3. NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/pytest_db_at_024.log
4. pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz --maxfail=1 -q | tee plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/pytest_cli_refined_mtz.log
Pitfalls To Avoid:
- Preserve device/dtype neutrality in bridge helpers; no hard-coded CPU conversions.
- Avoid breaking existing diagnostics keys; telemetry must be additive.
- Keep DB_AT_024 artifacts under the provided report directory; no stray outputs.
- Do not relax acceptance thresholds; telemetry enforcement should fail loudly when refined MTZ missing.
- Respect Environment Freeze; no installs or external data fetches.
- Ensure tests remain hermetic by mocking filesystem/MTZ where practical.
- Maintain CLI telemetry contract; run the CLI regression to confirm no regressions.
- Keep telemetry values serializable (native Python scalars/strings for HDF5/JSON).
If Blocked: Document the blocker in plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/blocked.md, append the summary and return conditions to docs/fix_plan.md Attempts History, and note the blocked state in galph_memory.md before pivoting focus.
Findings Applied:
- SCALE-003 — Enforce refined |F| usage by exposing telemetry; acceptance tests must fail on raw fallback.
- SCALE-004 — Couple calibration metadata with refined structure factors; diagnostics should surface provenance.
- DIAGNOSTICS-001 — Keep torch diagnostics schema authoritative and additive.
- TESTING-002 — Use CLI/bridge mocks to keep tests deterministic.
- TESTING-003 — Maintain selector hygiene with collect-only evidence before claiming Active status.
Pointers:
- dbex/nanobrag_bridge.py:843 — simulate_forward_once diagnostics payload
- dbex/nanobrag_bridge.py:1098 — simulate_forward_torch HKL handling
- tests/dbex/test_mapping_consistency.py:149 — DB_AT_024 acceptance test body
- docs/spec-db-tracing.md:20 — Torch diagnostics contract
- docs/TESTING_GUIDE.md:71 — DB_AT_024 selector requirements
Next Up (optional):
1) Teach DB_AT_024 to record refined geometry metadata (expt/refl provenance) in artifacts once telemetry lands.
Doc Sync Plan:
- After implementation, rerun collect-only + full DB_AT_024 logs (already scripted above) and update docs/TESTING_GUIDE.md §2 plus docs/development/TEST_SUITE_INDEX.md with the telemetry enforcement notes, referencing the new artifacts under plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/.
