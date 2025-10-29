# NANOBRAG-GOLDEN-001 — 2025-10-29T190533Z Planning Notes

## Reality Check
- `tests/fixtures/golden_data/simple_cubic/` still only contains `manifest.json` and `metadata.json`; canonical `.npy` tensors are absent.
- Latest capture logs under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T185313Z/` show torch outputs orders of magnitude below DiffBragg because the generator no longer reapplies `sqrt(spot_scale_override)` after deprecating pre-scaled structure factors.
- Parity smoke test artifacts (`tests/dbex/test_db_at_001_parity.py`) continue to land in `2025-10-29T181603Z/`, so new captures do not supersede stale evidence.

## Findings Reinforced
- SCALE-001 (structure factors must remain unscaled; avoid duplicate `sqrt(scale_override)` application).
- SCALE-002 (torch tensors require post-simulation sqrt scale to match DiffBragg magnitudes).

## Immediate Targets
1. Teach `scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden` to apply the required post-sim scale and actually emit the canonical `.npy` tensors plus manifest metadata into the fresh report directory and fixtures.
2. Update the parity harness loader/test to point at the canonical dataset path and emit artifacts into this loop's report directory.
3. Re-run `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001` once tensors are regenerated to validate metrics and thresholds.
