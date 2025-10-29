Summary: Advance DB_AT_001 parity harness from manifest-only coverage to metric-producing parity smoke with documented artifacts.
Mode: Parity
Focus: PARITY-HARNESS-002 — Implement DB-AT parity harness tests
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Artifacts: plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/
Do Now:
  1. PARITY-HARNESS-002.B1 (plans/active/PARITY-HARNESS-002/implementation.md) — Implement `compute_parity_metrics()` with correlation, RMSE, MSE, max|Δ|, sum ratio, and localization stats; add targeted unit coverage in `tests/dbex/test_db_at_001_parity.py`; tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k parity_metrics.
  2. PARITY-HARNESS-002.B2 (plans/active/PARITY-HARNESS-002/implementation.md) — Wire artifact writers that persist metrics JSON/CSV and overlay stubs under `parity_harness/`; ensure manifest checksum recorded; tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k artifact_emission.
  3. PARITY-HARNESS-002.B3 (plans/active/PARITY-HARNESS-002/implementation.md) — Extend fixtures to hydrate DiffBragg + torch forward tensors, seed RNG for determinism, and integrate metrics helper into DB_AT_001 parity test with conditional xfail; tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001.
  4. PARITY-HARNESS-002.C3 (plans/active/PARITY-HARNESS-002/implementation.md) — Update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with revised selector scope, env vars, and artifact paths; refresh docs/fix_plan.md Metrics/Artifacts lines; tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests -k DB_AT_001.
Priorities & Rationale:
- `docs/spec-db-conformance.md:23-26` (CONFORMANCE-001) requires DB_AT_001 to enforce correlation/localization thresholds with xfail diagnostics, motivating B1-B3 and step 4 doc sync.
- `docs/forward_equivalence.md:30-53` defines ROI metrics and acceptance strategy we must mirror for parity harness metric helper and xfail behavior.
- `docs/spec-db-core.md:20-40` (GEOMETRY-001) mandates `[panel, slow, fast]` ordering and square pixel guards that parity fixtures and metrics must respect.
- `docs/spec-db-tracing.md:10-24` (DIAGNOSTICS-001) prescribes trace/artifact layout, guiding B2 artifact writers and doc updates.
- `docs/TESTING_GUIDE.md:59-83` & `docs/development/TEST_SUITE_INDEX.md:5-23` (TESTING-003) require selector documentation and collect-only evidence once DB_AT_001 expands beyond manifest checks.
- `docs/spec-db-workflow.md:24-29` (MASKING-001) confirms sparse loss mask coverage is expected, ensuring metrics interpretation doesn’t false-positive failures.
How-To Map:
- `export KMP_DUPLICATE_LIB_OK=TRUE`
- `pytest -v tests/dbex/test_db_at_001_parity.py -k parity_metrics | tee plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/pytest_parity_metrics.log`
- `pytest -v tests/dbex/test_db_at_001_parity.py -k artifact_emission | tee plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/pytest_artifact_emission.log`
- `pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/pytest_db_at_001.log`
- `pytest --collect-only -q tests -k DB_AT_001 | tee plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/collect_db_at_001.log`
- `python scripts/generate_simple_cubic_golden.py --verify-manifest > plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/manifest_verify.log` (optional sanity before commits)
Pitfalls To Avoid:
- Skipping RNG seeding for torch stub, causing flaky metrics.
- Writing artifacts outside `plans/active/PARITY-HARNESS-002/reports/.../parity_harness/`.
- Forgetting to record manifest checksum alongside metric artifacts.
- Allowing DB_AT_001 to hard fail instead of conditional xfail on stubbed simulator gaps.
- Neglecting collect-only evidence before claiming selector Active status.
- Missing `KMP_DUPLICATE_LIB_OK=TRUE`, triggering OMP duplicate library faults.
- Omitting doc updates, leaving TESTING_GUIDE/TEST_SUITE_INDEX unsynchronized.
- Overwriting existing manifest fixtures instead of extending them.
- Ignoring square pixel/ordering guards when hydrating tensors.
- Leaving metrics helper untested, reducing confidence in thresholds.
If Blocked:
- If torch forward tensor generation remains stubbed and blocks thresholds, log diagnostic reason, set docs/fix_plan.md status to `blocked`, and capture artifact evidence in reports/2025-10-29T015235Z/ before pivoting.
- If golden dataset checksum mismatches, rerun generator to refresh manifest or document TODO + blocker in fix_plan Attempts History and galph_memory, then halt further steps.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Enforces DB_AT_001 selector thresholds with required env flags.
- GEOMETRY-001 — Preserves detector geometry and pixel pitch guards through fixtures.
- MASKING-001 — Interprets sparse loss mask coverage correctly in metric helper.
- DIAGNOSTICS-001 — Captures diagnostics and artifact paths for parity runs.
- TESTING-003 — Schedules collect-only evidence and documentation sync for selector changes.
Doc Sync Plan (Mandatory):
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests -k DB_AT_001 | tee plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/collect_db_at_001.log` — update docs/TESTING_GUIDE.md §2 parity row and docs/development/TEST_SUITE_INDEX.md Active tables with new scope & artifact link.
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k parity_metrics | tee plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/collect_parity_metrics.log` — document new unit selector or mark as sub-checklist in docs/TESTING_GUIDE.md §2.1 and ensure TEST_SUITE_INDEX references the helper coverage.
