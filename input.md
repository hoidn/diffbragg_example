Summary: Close MAP-SCALE-002 by finishing regression + doc sync for nanobrag CLI calibration metadata.
Mode: Parity
Focus: MAP-SCALE-002 — Nanobrag CLI calibration parity
Branch: integration
Mapped tests: pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration --maxfail=1 -q; pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
Artifacts: plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z/{summary.md,collect_db_at_024.log,pytest_cli_calibrated.log,pytest_db_at_024.log,doc_updates.md}

Do Now (hard validity contract)
- Implement: tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration — author a calibration-positive CLI test (mock args with `--torch-config`/`--refined-mtz`) that asserts `create_beam_config` receives flux/exposure/beamsize overrides, `create_crystal_config` toggles `apply_n_cells`, and `Simulator` is invoked with `beam_config`; update docs/TESTING_GUIDE.md::§2 Torch CLI and docs/development/TEST_SUITE_INDEX.md::DB_AT_024 with new CLI flag guidance and artifact expectations.
- Validate: export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md; pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration --maxfail=1 -q | tee plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z/pytest_cli_calibrated.log
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke | tee plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z/collect_db_at_024.log
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z/pytest_db_at_024.log

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. Implement calibration-positive assertions in `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration` (reuse existing mocks + fixture paths).
3. Update `docs/TESTING_GUIDE.md` §2 Torch CLI usage to describe `--torch-config`/`--refined-mtz` workflow and artifact capture; mirror selector entry in `docs/development/TEST_SUITE_INDEX.md`.
4. pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration --maxfail=1 -q | tee plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z/pytest_cli_calibrated.log
5. DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke | tee plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z/collect_db_at_024.log
6. DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z/pytest_db_at_024.log
7. Record doc diffs + command outputs in plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z/doc_updates.md (summary + links).

Pitfalls To Avoid
- Keep Environment Freeze: reuse existing calibration fixtures; do not download or install packages.
- Ensure new CLI test stays offline by mocking filesystem hits; no real MTZ parsing in unit test.
- Maintain device neutrality in assertions—do not hardcode CUDA-only assumptions.
- Preserve legacy behavior: defaults must still work without calibration metadata; test must target the positive path only.
- Capture collect-only output even if selector already known to pass; absence blocks closeout.
- Update both docs/TESTING_GUIDE.md and TEST_SUITE_INDEX together to avoid ledger drift.
- Retain SCALE-005 guard: the test should assert `apply_n_cells` only flips when metadata supplies counts.

If Blocked
- Store failure logs in plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z/blockers.md, flag MAP-SCALE-002 as blocked in docs/fix_plan.md, and add a galph_memory note citing the error signature and missing asset.

Findings Applied (Mandatory)
- SCALE-005 — Sample clipping engages only when N_cells + beam_config flow together; assert this in the calibration-positive test.
- SCALE-006 — Nanobrag CLI must forward DiffBragg `config_torch.json` metadata; new test + docs enforce this guard.
- TESTING-003 — Update testing docs/registry whenever selectors change status or get new artifacts.
- DOC-RUNTIME-004 — Runtime checklist remains pending; keep documentation consistent with freeze policy.

Pointers
- tests/dbex/test_refine_one_cli.py:150 — Existing CLI test scaffolding to extend for calibration assertions.
- dbex/refine_one.py:201 — Calibration load path to mirror in mocks.
- docs/TESTING_GUIDE.md:60 — DB_AT_024 selector documentation needing CLI updates.
- docs/development/TEST_SUITE_INDEX.md:27 — Registry row for DB_AT_024 requiring artifact refresh.
- plans/active/MAP-SCALE-002/reports/2025-11-05T000500Z/summary.md — Prior implementation evidence for calibration plumbing.

Next Up (optional)
1. Once docs/tests land, mark MAP-SCALE-002 done and archive artifacts.

Doc Sync Plan (Conditional)
- After `pytest` passes, rerun the `--collect-only` command (already in Do Now) and update docs/TESTING_GUIDE.md §2 + docs/development/TEST_SUITE_INDEX.md with fresh artifact timestamps; record summary in doc_updates.md.

Mapped Tests Guardrail
- Ensure both selectors collect (>0) during the `--collect-only` step; if collection fails, treat as block and note in blockers.md before exiting.
