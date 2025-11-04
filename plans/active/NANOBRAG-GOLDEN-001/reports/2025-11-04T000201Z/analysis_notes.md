# NANOBRAG-GOLDEN-001 — 2025-11-04T000201Z Analysis Notes

## Observations
- Current checkout lacks ROI `.npz` payloads under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-03T233556Z/roi_triptychs/`; only `index.json` remains, so triptych artifacts were generated in a different repo checkout.
- `manifest.json` inside both `plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-03T233556Z/golden_dataset/` and `tests/fixtures/golden_data/simple_cubic/` records the generator command rooted at `/home/ollie/Documents/diffbragg_example_2/diffbragg_example`, confirming the canonical capture ran outside this workspace.
- Loaded `tests/fixtures/golden_data/simple_cubic/{bragg_diffbragg.npy, bragg_torch.npy, loss_mask_panel_0.npy}` and recomputed ROI metrics via `prepare_refinement_inputs`; global masked correlation remains -0.0041 with torch `nonzero` pixel count 5.6M vs DiffBragg 97k.
- Example ROI (roi_idx=5, bbox 715:727 × 429:441) shows DiffBragg peak at (6,6) with 1.0e3 photons while torch peak lands at (11,7) with 2.4e2 photons; even mirrored/transpose transforms do not align peaks, indicating a systematic spatial offset rather than axis inversion.

## Metrics
- `median_corr=-0.0358`, `global_corr=-0.0041`, `localization_success_rate=5.6%` (recomputed from fixtures).
- `torch_max=3.90e4`, `diffbragg_max=3.62e4`, `torch_sum(mask)=8.0e4`, `diff_sum(mask)=9.2e5`.

## Next Steps
1. Patch `scripts/generate_simple_cubic_golden.py::compute_roi_metrics` to emit per-ROI peak coordinates, offsets, and `roi_XXXX.npz` filenames inside `index.json` so offsets are inspectable without re-running python helpers.
2. Re-run canonical generator in this checkout with `--roi-dump` to repopulate `plans/active/NANOBRAG-GOLDEN-001/reports/<new-ts>/` and fixtures with locally scoped tensors.
3. Re-run `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke` capturing logs in the new report directory.
