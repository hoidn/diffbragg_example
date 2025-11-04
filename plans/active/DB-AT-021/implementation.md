# DB-AT-021 — Mask semantics guard

## Phase A — Baseline validation & probes
- [ ] A1: Confirm canonical assets present (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`); log `ls -lh` snapshot under reports.
- [ ] A2: Instantiate `DataLoad` with canonical args (`mtzFile`, `maskFile`, etc.) and capture summary of available attributes (data shape, background coverage, mask availability once wired).
- [ ] A3: Record mask coverage metrics (True fraction, false pixel count) and reconcile with `docs/spec-db-core.md:29-55` expectations (True=include, `(background >= 0) ∧ trusted_mask`).

## Phase B — Implementation & testing
- [ ] B1: Extend `dbex.data_load.DataLoad` to hydrate trusted mask (`args.maskFile`), expose detector/beam/crystal attributes, and enforce polarity guard (ValueError when majority False).
- [ ] B2: Author `tests/dbex/test_mask_semantics.py` with DB_AT_021 tests:
  - `test_DB_AT_021_trusted_mask_shape_and_polarity`: asserts dtype/shape, skip when mask missing, coverage sanity (>0.5 True).
  - `test_DB_AT_021_loss_mask_consistency`: uses `prepare_refinement_inputs` to confirm zeroing and `(background >= 0) & trusted_mask` equivalence.
- [ ] B3: Run targeted commands:
  - `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_mask_semantics.py -k DB_AT_021`
  - `pytest --collect-only tests -k DB_AT_021`
  - (Optional) `pytest -v tests/ -k DB_AT_021 or DB_AT_020` for regression sweep after code changes.

## Phase C — Documentation & artifact sync
- [ ] C1: Persist artifacts under `plans/active/DB-AT-021/reports/<timestamp>/` (pytest logs, collect logs, mask_metrics.json).
- [ ] C2: Update `docs/TESTING_GUIDE.md` DB_AT_021 row to Active with canonical metrics, environment flags, artifact paths.
- [ ] C3: Sync `docs/development/TEST_SUITE_INDEX.md` entry + append new findings to `docs/findings.md` if mask insights captured; annotate fix plan Attempts History with metrics.
