Summary: Verify DB_AT_001 parity harness exit criteria and close PARITY-HARNESS-002 ledger with fresh artifacts and documentation updates.
Mode: Parity
Focus: PARITY-HARNESS-002 — Implement DB-AT parity harness tests
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Artifacts: plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/{parity_harness/,closing/}
Do Now:
  1. PARITY-HARNESS-002 E1 (plans/active/PARITY-HARNESS-002/implementation.md) — Run parity suite + collect-only to refresh metrics and evidence; capture logs under the new artifact path. tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001
  2. PARITY-HARNESS-002 E2 (plans/active/PARITY-HARNESS-002/implementation.md) — Update docs/fix_plan.md status to done with final Attempts History entry and sync selector docs to point at 2025-10-29T022212Z logs. tests: none — documentation updates only
  3. PARITY-HARNESS-002 E3 (plans/active/PARITY-HARNESS-002/implementation.md) — Author closing summary and outstanding simulator TODOs under closing/ referencing applied findings; prep initiative for archival. tests: none — evidence write-up only
Priorities & Rationale:
- docs/spec-db-conformance.md:23-26 — Exit criteria demand DB_AT_001 thresholds with diagnostics when unmet, so we must revalidate metrics before closure.
- docs/forward_equivalence.md:48-53 — Selector SHOULD xfail yet emit artifacts, guiding the parity rerun and closure evidence.
- docs/spec-db-tracing.md:15-19 — First-divergence tracing remains mandatory, so refreshed artifacts must keep trace metadata intact.
- docs/TESTING_GUIDE.md:56-90 — Registry sync requires updated collect-only logs whenever selector evidence moves.
- docs/development/TEST_SUITE_INDEX.md:14-36 — Test index must mirror selector status/log paths prior to marking the initiative done.
How-To Map:
- Ensure artifacts directory exists: mkdir -p plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/{parity_harness,closing}
- Run parity suite with logs: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/pytest_db_at_001.log
- Collect-only evidence: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/collect_db_at_001.log
- Copy parity artifacts emitted by the test into plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/parity_harness/
- Update docs/fix_plan.md status + Attempts History and adjust docs/TESTING_GUIDE.md & docs/development/TEST_SUITE_INDEX.md references to the new collect log
- Draft closing summary in plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/closing/summary.md including outstanding simulator TODOs
Pitfalls To Avoid:
- Forgetting KMP_DUPLICATE_LIB_OK=TRUE will deadlock MKL threads.
- Overwriting existing manifest checksums or synthetic tensors.
- Dropping the parity test xfail reason when rerunning the suite.
- Mislabeling artifact paths in docs, causing registry drift.
- Emitting closing notes outside the designated artifacts directory.
- Treating stub correlation failure as regression instead of expected diagnostic output.
- Skipping findings references in the closing summary.
If Blocked:
- If parity suite hard-fails, capture logs in the artifact directory, mark PARITY-HARNESS-002 blocked in docs/fix_plan.md with failure summary, and notify supervisor via galph_memory Attempts History.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Keeps DB_AT_001 selector + env guard aligned while finalizing closure.
- DIAGNOSTICS-001 — Ensures diagnostics artifacts remain compliant when regenerating logs.
- TESTING-003 — Drives collect-only evidence and doc sync before marking selector Active.
- PARITY-001 — Maintains deterministic first-divergence metadata during rerun and closing summary.
Doc Sync Plan (Mandatory):
- Selector DB_AT_001 (tests/dbex/test_db_at_001_parity.py -k DB_AT_001): run KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 and save to plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/collect_db_at_001.log; update docs/TESTING_GUIDE.md §2.1 and docs/development/TEST_SUITE_INDEX.md parity row with the new artifact reference.
