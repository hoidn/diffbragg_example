# NANOBRAG-GOLDEN-001 — Canonical capture recovery prep (2025-10-29T091339Z)

## Observations
- Reviewed 2025-10-29T084244Z canonical_capture.log; DiffBragg baseline peaks at 3.6e4 but torch stack remains all zeros (max=0.0, sum=0.0).
- `torch_hkl_debug.json` confirms 69,614 reflections map in-range, so zero output is not caused by missing HKL coverage.
- Artifact directories exist under diffbragg_example_2 mirror; current repo lacks copied `.npy` tensors, so fixtures still point at fallback manifest only.

## Working Hypotheses
- Torch stack underflows because we never apply the DiffBragg global scale (`mdl_parm["scale"] ≈ 3.19e17`) when calling `TorchSimulator.run()`.
- CLI references (`nanobrag_torch.__main__.py:1201-1225`) apply a configurable scale before writing images; our generator bypasses that path.
- Alternatively, ROI mask multiplication may be zeroing tensors if detector mask polarity or ROI bounds are mis-specified—needs instrumentation.

## Next Diagnostic Steps
1. Instrument `scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden` to log the maximum intensity before applying any mask/scale (`TorchSimulator.run()` raw output) and confirm it's non-zero but underflowing.
2. Propagate the DiffBragg global scale (and/or simulated fluence) into the torch capture path—either by multiplying the raw tensor or wiring a scale term through `TorchBeamConfig`/`TorchCrystalConfig`.
3. Re-run canonical capture into `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T091339Z/golden_dataset/`, confirm `bragg_torch.npy` has non-zero maxima, and update fixtures/manifests accordingly.
4. Execute `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001` to validate thresholds once tensors are non-zero; archive logs under this report root.

## Findings Links
- CONFIG-001 (`docs/findings.md`) — geometry/config mapping cross-checks remain applicable when debugging ROI masks.
- DIFFBRAGG-001 — ensures the rebuilt DiffBragg baseline we compare against is correct; no regression detected.
