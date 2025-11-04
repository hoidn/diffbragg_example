Summary: Align DB-AT-001 parity harness artifacts/docs with the canonical 2025-11-04 capture and rerun the smoke selector.
Mode: Parity
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/

Do Now:
- Implement: tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity.test_db_at_001_parity_smoke — repoint parity harness artifacts to plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/, refresh messaging for canonical metrics, and ensure manifest checksum + metadata remain logged.
- Doc: docs/TESTING_GUIDE.md §2 (DB_AT_001 parity entry) and docs/development/TEST_SUITE_INDEX.md (parity harness row) — update collection log, artifact directory, and status notes to the 2025-11-04 canonical capture.
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/pytest_db_at_001.log
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. mkdir -p plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z
3. Edit tests/dbex/test_db_at_001_parity.py per Do Now (artifact path, messaging), then update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md parity rows.
4. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/pytest_db_at_001.log
5. ls plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/parity_harness to confirm metrics.json, metrics.csv, first_divergence.json, predicted.npy, target.npy
6. git status --short

Pitfalls To Avoid:
- Do not modify or reinstall environment packages (Environment Freeze).
- Keep canonical fixtures in tests/fixtures/golden_data/simple_cubic/ untouched; only update test/doc references.
- Ensure artifact_dir points to 2025-11-04T020930Z (avoid reusing 2025-10-29 paths).
- Preserve manifest checksum + metadata in write_parity_artifacts calls; no silent drops.
- Run pytest with KMP_DUPLICATE_LIB_OK=TRUE to avoid MKL duplication errors.
- Do not tighten DB-AT-001 thresholds beyond spec (≥0.2 corr, ≥0.9 localization) in this loop.
- Sync docs after code passes; keep TESTING_GUIDE and TEST_SUITE_INDEX consistent.
- Record pytest log under artifacts directory; no stdout-only runs.
- Avoid deleting prior report directories—new evidence must live under 2025-11-04T020930Z.
- Leave ROI offset summary generation untouched (golden dataset already validated).

If Blocked:
- If parity test fails or artifacts missing, capture the failing command output, log the minimal error in plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/summary.md, append a blocked Attempts History entry in docs/fix_plan.md, update galph_memory.md with state=planning, and notify supervisor before retrying.

Findings Applied (Mandatory):
- CONFIG-001 — Maintain bridge mapping invariants when editing parity harness (beam center swap, mask polarity).
- MANIFEST-001 — Keep manifest paths/checksums local to this checkout when updating docs/test messaging.
- SCALE-001 — Do not reapply structure-factor scaling when comparing canonical tensors.
- SCALE-002 — Preserve torch post-scale outputs (no extra normalization) when logging parity metrics.
- HKL-ORIENT-001 — Ensure source→sample vector conventions remain intact in parity docs/tests.
- TESTING-003 — Update TESTING_GUIDE and TEST_SUITE_INDEX in lockstep after verifying pytest collection.

Pointers:
- tests/dbex/test_db_at_001_parity.py:708 — parity smoke test requiring artifact path refresh.
- docs/TESTING_GUIDE.md:87 — DB_AT_001 parity harness entry to sync with new artifacts.
- docs/development/TEST_SUITE_INDEX.md:14 — Parity harness registry row with outdated collection log.
- plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/summary.md — Current loop evidence + next-step notes.

Next Up (optional):
- D2 knowledge-base update once parity rerun + docs sync complete.
