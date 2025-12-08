# DB-AT-021 — Mask Semantics Guard

## Phase A — Reality Check & Inputs
- [ ] **A1 — Dataset availability**: Confirm refGeom assets (`refGeom.expt`, `refGeom.refl`, `747_mask.pkl`) remain in the workspace (cross-ref DB-AT-SUITE-CARE-001 Phase B.2 asset validation from i=143); note skip behavior when assets missing.
- [ ] **A2 — Spec alignment**: Reconcile mask polarity semantics with `docs/spec-db-core.md:47-55` (normative mask polarity + loss_mask construction), `docs/dials_api.md:45-62` (Flags.integrated bitmask), and `docs/architecture.md:165-178` (mask precedence rules) to ensure test expectations align with spec.
- [ ] **A3 — Baseline probe**: Run a lightweight DataLoad inspection (trusted_mask shape/polarity counts, loss_mask construction validation, sample ROI mask intersection) and capture results under `plans/active/DB-AT-021/reports/<timestamp>/baseline_probe.md` to ground assertions.

## Phase B — Harness Implementation
- [ ] **B1 — Test scaffold**: Introduce `tests/dbex/test_mask_semantics.py` with `TestDB_AT_021_MaskSemantics` covering DB_AT_021; add fixture that instantiates `DataLoad` (skips if `refGeom.expt`/`refGeom.refl` missing) and scopes canonical assets.
- [ ] **B2 — Mask polarity checks**: Assert `trusted_mask` is boolean array with shape matching panel dimensions; validate `loss_mask = (background >= 0) & trusted_mask` construction matches spec; verify ROI mask intersection produces expected pixel counts.
- [ ] **B3 — Precedence guards**: Test background sentinel handling (`background == -1` excluded from loss_mask); validate trusted=False pixels excluded even if background >= 0; cross-check with reflection table `flags` column (Flags.integrated bitmask).

## Phase C — Documentation & Registry Sync
- [ ] **C1 — Evidence capture**: Run `pytest -v tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics -k DB_AT_021` and `pytest --collect-only tests -k DB_AT_021`, archiving logs under this initiative.
- [ ] **C2 — Docs update**: Promote DB_AT_021 rows in `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` to Active with artifact paths, command selectors, and referenced findings (e.g., MASKING-001, TESTING-003, CONFORMANCE-001).
- [ ] **C3 — Ledger sync**: Append Attempts History entries to `docs/fix_plan.md` with metrics/commands/artifacts, update `docs/findings.md` if new mask handling pitfalls emerge, and mark the initiative ready for closure once exit criteria are met.
