Summary: Add a manifest checksum assertion to the DB_AT_001 parity smoke test and refresh docs/artifacts so NANOBRAG-GOLDEN-001 can close cleanly.
Mode: none
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T030000Z/

Do Now (hard validity contract)
- Focus: NANOBRAG-GOLDEN-001
- Implement: tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke — assert manifest_checksum equals 2d1f8d671a6b051b23dd7a059f9fd8ff5605389bbe9a8e72cb44cbd7a8567aee and point artifact_dir to plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T030000Z before writing parity artifacts.
- Sync Docs: docs/TESTING_GUIDE.md, docs/development/TEST_SUITE_INDEX.md — update parity harness rows with the 2025-11-04T030000Z report paths/log names and note the checksum guard.
- Update Ledger: docs/fix_plan.md — add a completion attempt for the checksum guard rerun and flip status to done once artifacts/logs are in place.
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T030000Z/pytest_db_at_001.log
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T030000Z/

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export REPORT_DIR=plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T030000Z
3. mkdir -p "$REPORT_DIR"/parity_harness
4. Edit tests/dbex/test_db_at_001_parity.py to harden the manifest checksum assert and bump artifact_dir to "$REPORT_DIR"/parity_harness (leave thresholds unchanged).
5. Edit docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md parity rows to replace 2025-11-04T020930Z with 2025-11-04T030000Z and mention the checksum assertion.
6. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee "$REPORT_DIR"/pytest_db_at_001.log
7. KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_db_at_001_parity.py | tee "$REPORT_DIR"/collect_db_at_001_parity.log
8. Confirm "$REPORT_DIR"/parity_harness/parity_harness/ contains metrics.json, metrics.csv, predicted.npy, target.npy, first_divergence.json; capture their checksums if diffs appear.
9. Update docs/fix_plan.md Attempts History + status (set to done) referencing the new report directory and pytest log.

Pitfalls To Avoid
- Do not touch fixtures in tests/fixtures/golden_data/simple_cubic; only the parity test and docs should change.
- Keep correlation/localization thresholds at 0.2 and 0.9; no tightening this loop.
- Preserve existing artifact naming (pytest_db_at_001.log, collect_db_at_001_parity.log, parity_harness/ subdir) so docs remain accurate.
- Ensure REPORT_DIR uses the new timestamp; do not overwrite 2025-11-04T020930Z evidence.
- Export KMP_DUPLICATE_LIB_OK=TRUE for both pytest commands to avoid MKL contention failures.
- Leave write_parity_artifacts semantics untouched; only pass the new artifact_dir and assert on manifest_checksum.
- Avoid changing parity metric calculations; the goal is a guard, not new tolerances.
- Document any unexpected failures in docs/fix_plan.md before retrying.

If Blocked
- If the manifest checksum assertion fails, capture the observed checksum in "$REPORT_DIR"/summary.md, mark NANOBRAG-GOLDEN-001 as blocked in docs/fix_plan.md with the failure signature, and ping supervisor before modifying fixtures.

Findings Applied (Mandatory)
- MANIFEST-001 — Guard fixture availability and checksum integrity when emitting manifests; the new assert enforces this.
- SCALE-001 — No extra sqrt(scale_override) multiplication; leave generator outputs untouched when asserting metrics.
- SCALE-002 — Preserve global post-simulation scaling; metrics comparison must reflect canonical tensors.
- GEOMETRY-002 — Analytic XYZ inversion remains the source of canonical geometry; the checksum guard protects the aligned dataset.
- PARITY-001 — Maintain deterministic artifact emission (first_divergence.json, parity metrics) under the refreshed timestamp.
- TESTING-003 — Update Testing Guide and Test Suite Index in lockstep with new collection logs and ensure the selector stays Active.

Pointers
- docs/fix_plan.md:15 — NANOBRAG-GOLDEN-001 exit criteria and latest attempts.
- plans/active/NANOBRAG-GOLDEN-001/implementation.md:21 — Phase D checklist showing D3 still open for ledger wrap-up.
- tests/dbex/test_db_at_001_parity.py:746 — Location to add the manifest checksum assertion and bump artifact_dir.
- docs/TESTING_GUIDE.md:87 — Parity harness row needing the new timestamp/log references.
- docs/development/TEST_SUITE_INDEX.md:14 — Mirror parity row for selector status/log paths.
- docs/findings.md:3 — GEOMETRY-002 knowledge base entry recorded this loop.

Next Up (optional)
- Review docs/index.md parity references after closure to confirm canonical capture metadata is surfaced.
