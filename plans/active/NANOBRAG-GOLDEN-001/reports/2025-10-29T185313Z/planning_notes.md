# NANOBRAG-GOLDEN-001 — 2025-10-29T185313Z Planning Notes

## Reality Check
- `tests/fixtures/golden_data/simple_cubic/` currently holds only `manifest.json` and `metadata.json`; canonical `.npy` payloads are absent.
- Latest capture directory (`plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T212500Z/golden_dataset/`) also lacks `bragg_diffbragg.npy` and `bragg_torch.npy`, so manifest references stale files.
- `metrics.json` from the same run reports `diffbragg_max=3.62e4` vs `torch_max=6.91e-05`, i.e., torch intensities are ~5×10^8 smaller than DiffBragg, yielding median correlation ≈0 and localization ≈5.6%.
- `tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity.test_db_at_001_parity_smoke` still emits artifacts under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T181603Z/`, so refreshed runs cannot supersede earlier evidence.

## Findings Applied
- Added SCALE-002 to `docs/findings.md` capturing the need to reapply √(spot_scale_override) after the nanobrag_torch forward pass instead of pre-scaling structure factors.

## Next Steps
1. Teach `scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden` to scale torch outputs by √(mdl_parm["scale"]) and persist `.npy` tensors + manifest under a new timestamp (`2025-10-29T185313Z`).
2. Refresh fixtures directory with the scaled tensors and regenerated manifest/metadata.
3. Update `tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity.test_db_at_001_parity_smoke` to write artifacts into the new reports directory for this loop.
4. Re-run `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001`, capture logs, and inspect revised metrics before enforcing thresholds.
