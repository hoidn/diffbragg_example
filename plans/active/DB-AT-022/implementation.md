# DB-AT-022 — Background sentinel guard

## Phase A — Asset validation & sentinel probes
- [ ] A1: Verify canonical assets exist (`scaled.mtz`, `refGeom.expt`, `refGeom.refl`, `747_mask.pkl`); record snapshot of file presence in planning report.
- [ ] A2: Instantiate `DataLoad` with canonical inputs and capture baseline metrics (data/background shapes, ROI count, bbox sample) to confirm prerequisites from DB-AT-020/021 remain valid.
- [ ] A3: Probe `background_image` sentinel coverage: compute sentinel mask (`np.isclose(background, -1.0)`), ROI union mask derived from bbox/pids, and summarize coverage ratios + overlap counts.

## Phase B — Implementation & testing
- [ ] B1: Harden `dbex.nanobrag_bridge.prepare_refinement_inputs` with an explicit sentinel guard (ensure `background_image` uses -1 outside ROIs and raise descriptive `ValueError` when unexpected values are encountered).
- [ ] B2: Author `tests/dbex/test_background_semantics.py` to cover DB_AT_022 acceptance criteria:
  - `test_DB_AT_022_sentinel_complement`: asserts sentinel mask equals the complement of ROI union, zero overlap, coverage aligns with ROI area metadata.
  - `test_DB_AT_022_metrics_alignment`: logs ROI/background coverage metrics (ROI count, sentinel_fraction, background_fraction, mismatch counts) and ensures loss mask derived from `prepare_refinement_inputs` respects sentinel guard.
- [ ] B3: Execute targeted selectors:
  - `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_background_semantics.py -k DB_AT_022`
  - `pytest --collect-only tests -k DB_AT_022`
  - Optional regression sweep: `pytest -v tests/ -k DB_AT_02`

## Phase C — Documentation & artifact sync
- [ ] C1: Archive artifacts under `plans/active/DB-AT-022/reports/<timestamp>/` (pytest logs, collect logs, sentinel_metrics.json, roi_coverage.json).
- [ ] C2: Promote DB_AT_022 entries in `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` to Active with command selectors, environment flags, artifact paths, applied findings.
- [ ] C3: Update `docs/fix_plan.md` Attempts History with commands/metrics, note sentinel guard rationale, and append new durable insight to `docs/findings.md` if additional background semantics lessons emerge.
