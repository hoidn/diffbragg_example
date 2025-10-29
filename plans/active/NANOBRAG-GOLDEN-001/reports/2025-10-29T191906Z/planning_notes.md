# NANOBRAG-GOLDEN-001 Loop 2025-10-29T191906Z — Planning Notes

## Reality Checks
- `tests/fixtures/golden_data/simple_cubic/` only contains `manifest.json` and `metadata.json`; canonical `.npy` tensors are missing despite manifest entries.
- Canonical capture directory `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T190533Z/golden_dataset/` lacks `legacy/bragg_diffbragg.npy`, `torch/bragg_torch.npy`, and per-panel tensors; only configs/metrics remain.
- Manifest `generator_command` points to `/home/ollie/Documents/diffbragg_example_2/...`, indicating the last capture ran from a different checkout; current workspace never received the tensor payloads.

## Implications
- Exit Criterion 1 (canonical tensors present in fixtures) remains unmet; parity loader still falls back to synthetic data.
- Checklist items A3/B1/B3/C1 in `implementation.md` are still open because tensors and manifest payloads are absent.
- DB_AT_001 parity evidence from `2025-10-29T190533Z` is stale; without the tensors the harness cannot consume canonical data for validation.

## Next Focus
- Re-run canonical capture in this workspace (or restore missing `.npy` files) so fixtures and golden_dataset directories contain the tensors referenced by the manifest.
- Harden generator/fixture copy logic to fail loudly when tensor files are missing before manifest emission.
- Re-execute `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001` once tensors land to confirm Active selector still collects.
