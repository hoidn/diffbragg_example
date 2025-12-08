# DB-AT-020 — Reflection Ingestion Sanity

## Phase A — Reality Check & Inputs
- [x] **A1 — Dataset availability**: Confirm refGeom assets (`scaled.mtz`, `refGeom.expt`, `refGeom.refl`) remain in the workspace; note skip behavior when `refGeom.refl` is absent (mirror smoke fixture guard). ✅ 2025-12-08 (Loop i=145)
- [x] **A2 — Spec alignment**: Reconcile bbox semantics with `docs/spec-db-core.md:22`, `docs/dials_api.md:10-32`, and architecture runtime guards (`docs/architecture.md:122`) to ensure exclusive upper bounds and panel alignment requirements are reflected in test expectations. ✅ 2025-12-08 (Loop i=145)
- [x] **A3 — Baseline probe**: Run a lightweight DataLoad inspection (panels count, ROI tally, sample bbox deltas) and capture results under `plans/active/DB-AT-020/reports/<timestamp>/summary.md` to ground assertions. ✅ 2025-12-08 (Loop i=145)

## Phase B — Harness Implementation
- [x] **B1 — Test scaffold**: Introduce `tests/dbex/test_reflection_ingestion.py` with `TestReflectionIngestion` covering DB_AT_020; add fixture that instantiates `DataLoad` (skips if `refGeom.refl` is missing) and scopes canonical assets. ✅ 2025-12-08 (Loop i=146)
- [x] **B2 — Bbox exclusivity checks**: Assert every ROI bbox satisfies `x1 > x0`, `y1 > y0`, upper bounds within panel dimensions, and slicing `dl.data[pid, y0:y1, x0:x1]` / `dl.background_image` matches expected shapes. ✅ 2025-12-08 (Loop i=146)
- [x] **B3 — Panel ordering guards**: Validate reflection table `panel` column aligns with `dl.pids`, verify `dl.pids` integers fall within detector range, and ensure bbox arrays remain length-synced with `pids`. ✅ 2025-12-08 (Loop i=146)

## Phase C — Documentation & Registry Sync
- [x] **C1 — Evidence capture**: Run `pytest -v tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox` (plus any companion tests) and `pytest --collect-only tests -k DB_AT_020`, archiving logs under this initiative. ✅ 2025-12-08 (Loop i=147)
- [x] **C2 — Docs update**: Promote DB_AT_020 rows in `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` to Active with artifact paths, command selectors, and referenced findings (e.g., CONFORMANCE-001, TESTING-003). ✅ 2025-12-08 (Loop i=147)
- [x] **C3 — Ledger sync**: Append Attempts History entries to `docs/fix_plan.md` with metrics/commands/artifacts, update `docs/findings.md` if new ingestion pitfalls emerge, and mark the initiative ready for closure once exit criteria are met. ✅ 2025-12-08 (Loop i=147)
