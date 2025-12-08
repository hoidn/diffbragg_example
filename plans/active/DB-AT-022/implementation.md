# DB-AT-022 — Background sentinel guard

## Phase A — Asset validation & sentinel probes
- [x] A1: Verify canonical assets exist (`scaled.mtz`, `refGeom.expt`, `refGeom.refl`, `747_mask.pkl`); record snapshot of file presence in planning report. **(Loop i=151, 2025-12-08T180000Z: COMPLETE — cross-ref i=143 validation, 4/4 assets VALID)**
- [x] A2: Instantiate `DataLoad` with canonical inputs and capture baseline metrics (data/background shapes, ROI count, bbox sample) to confirm prerequisites from DB-AT-020/021 remain valid. **(Loop i=151: COMPLETE — data.shape=(1,2527,2463), 92 ROIs, all 12×12)**
- [x] A3: Probe `background_image` sentinel coverage: compute sentinel mask (`np.isclose(background, -1.0)`), ROI union mask derived from bbox/pids, and summarize coverage ratios + overlap counts. **(Loop i=151: COMPLETE — Case A: Perfect match, overlap=0, complement_match=True)**

## Phase B — Implementation & testing
- [x] B1: Harden `dbex.nanobrag_bridge.prepare_refinement_inputs` with an explicit sentinel guard (ensure `background_image` uses -1 outside ROIs and raise descriptive `ValueError` when unexpected values are encountered). **(Prior loop: guard implemented in `dbex/refinement/inputs.py:145-186`)**
- [x] B2: Author `tests/dbex/test_background_semantics.py` to cover DB_AT_022 acceptance criteria: **(Prior loop: test file authored with 3 tests)**
  - `test_DB_AT_022_sentinel_complement`: asserts sentinel mask equals the complement of ROI union, zero overlap, coverage aligns with ROI area metadata.
  - `test_DB_AT_022_metrics_alignment`: logs ROI/background coverage metrics (ROI count, sentinel_fraction, background_fraction, mismatch counts) and ensures loss mask derived from `prepare_refinement_inputs` respects sentinel guard.
- [x] B3: Execute targeted selectors: **(Loop i=152, 2025-12-08T200000Z: COMPLETE — 3/3 PASSED, 12.61s runtime)**
  - `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_background_semantics.py -k DB_AT_022`
  - `pytest --collect-only tests -k DB_AT_022`
  - Optional regression sweep: `pytest -v tests/ -k DB_AT_02`

## Phase C — Documentation & artifact sync
- [x] C1: Archive artifacts under `plans/active/DB-AT-022/reports/<timestamp>/` (pytest logs, collect logs, sentinel_metrics.json, roi_coverage.json). **(Loop i=152, 2025-12-08T200000Z: COMPLETE — pytest_db_at_022.log, collect_db_at_022.log archived)**
- [x] C2: Promote DB_AT_022 entries in `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` to Active with command selectors, environment flags, artifact paths, applied findings. **(Loop i=152, 2025-12-08T200000Z: COMPLETE — both registries updated with Active status)**
- [x] C3: Update `docs/fix_plan.md` Attempts History with commands/metrics, note sentinel guard rationale, and append new durable insight to `docs/findings.md` if additional background semantics lessons emerge. **(Loop i=152, 2025-12-08T200000Z: COMPLETE — Attempts History entry added, no new findings needed)**
