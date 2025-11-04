Summary: Sync DB_AT_024 documentation with the new structure-factor telemetry guard.
Mode: Docs
Focus: MAP-SCALE-004 — Zero-iteration telemetry parity
Branch: integration
Mapped tests:
- pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
- pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
Artifacts: plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z/
Do Now:
- MAP-SCALE-004: Implement: docs/TESTING_GUIDE.md::<DB_AT_024 selector row> + docs/development/TEST_SUITE_INDEX.md::<DB_AT_024 entry> — document telemetry requirements (hkl_source/count/mean/path), refresh metrics/artifact references to 2025-11-05T220000Z, and call out SCALE-007 guardrail. Validate: pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke; pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1.
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke | tee plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z/collect_db_at_024.log
3. NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z/pytest_db_at_024.log
Pitfalls To Avoid:
- Do not touch production bridge code; this loop is documentation-only.
- Keep telemetry field names exact (`hkl_source`, `hkl_n_reflections`, `hkl_mean_amplitude`, `hkl_path`).
- Reference the latest artifacts directory (2025-11-05T220000Z) and note metrics verbatim.
- Maintain selector status tables (no column drift) when editing docs.
- Ensure SCALE-007 stays marked Active and cross-linked in notes.
- Capture pytest output under the new artifact directory via tee.
- Respect Environment Freeze—no package installs or environment mutations.
- Preserve markdown table formatting (pipes aligned, no stray spaces causing parser issues).
If Blocked: Record the blocking issue in plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z/blocked.md, add the summary + return conditions to docs/fix_plan.md Attempts History, flag the focus as blocked in galph_memory.md, and pivot per loop discipline.
Findings Applied:
- SCALE-003 — Refined |F| amplitudes must be present for zero-iteration parity; telemetry documents their provenance.
- SCALE-004 — Calibration metadata and refined structure factors travel together; docs must reinforce this contract.
- SCALE-005 — Bridge telemetry should continue noting `n_cells_applied` so sample clipping guardrails stay discoverable.
- SCALE-007 — New guard: zero-iteration diagnostics must emit structure-factor telemetry and DB_AT_024 fails on raw fallbacks.
- DIAGNOSTICS-001 — Torch diagnostics schema changes must be additive and documented.
- TESTING-003 — Selector registry updates require fresh collect-only evidence and artifact references.
Pointers:
- dbex/nanobrag_bridge.py:843 — Telemetry-enabled `simulate_forward_once` signature and docstring.
- tests/dbex/test_mapping_consistency.py:339 — DB_AT_024 telemetry assertions that docs need to describe.
- docs/TESTING_GUIDE.md:71 — DB_AT_024 selector table row requiring telemetry updates.
- docs/development/TEST_SUITE_INDEX.md:27 — DB_AT_024 registry entry to sync with telemetry details.
- docs/fix_plan.md:67 — MAP-SCALE-004 Attempts History noting doc/test sync is still outstanding.
Next Up (optional): 1) Audit CLI docs for refined telemetry references once DB_AT_024 documentation is refreshed.
