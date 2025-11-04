# DB-AT-010 Planning Notes — 2025-11-04T065345Z

## Focus
Establish DB-AT-010 gradient correctness guard: deliver differentiable masked-loss helper plus gradcheck-based acceptance selector for crystal/detector/beam/model parameters.

## Key Observations
- Canonical assets (refGeom.expt/refl, scaled.mtz, 747_mask.pkl) already consumed by mapping/ingestion selectors; `DataLoad` provides aligned arrays suitable for gradcheck reuse (background-subtracted targets, bbox, pids).
- Current `simulate_forward_once` returns NumPy arrays by detaching simulator output (`panel_output.cpu().detach().numpy()`), which strips gradients. A torch-return path (or new helper) is required to feed `torch.autograd.gradcheck`.
- SCALE-002 handling multiplies by `np.sqrt(spot_scale_override)`; to keep gradients with respect to scale we must perform the sqrt/multiply in torch (and allow tensor inputs).
- Testing Strategy §4.1 and `nanoBragg/tests/test_gradients.py` demonstrate tolerances (`eps=1e-6`, `atol=1e-5`, `rtol=5e-2`) and environment guard (`NANOBRAGG_DISABLE_COMPILE=1`) that we must mirror; guard fixture can skip when the flag is absent.
- Gradcheck coverage must exercise at least one parameter from each category called out in spec (`docs/spec-db-runtime.md` §4.1): crystal cell length/angle, detector distance, beam wavelength, and model-scale parameter (fluence or spot scale). Metrics JSON should capture finite-difference vs analytical gradient deltas for traceability.

## References
- docs/spec-db-runtime.md §4.1 (Gradient profile requirements)
- docs/development/testing_strategy.md §4 (Gradcheck methodology & tolerances)
- docs/pytorch_runtime_checklist.md §§1–3 (vectorization/device & compile guard)
- dbex/nanobrag_bridge.py::simulate_forward_once (NumPy detachment to fix)
- nanoBragg/tests/test_gradients.py (reference implementation pattern)

## Next Steps (Do Now scaffold)
1. Refactor bridge helper to support torch outputs + masked MSE utility preserving gradients and SCALE-* findings.
2. Implement DB-AT-010 gradcheck pytest suite with environment guard, parameterized coverage, and metrics emission under `$DBAT010_ARTIFACT_DIR`.
3. Capture pytest + collect-only logs, promote selector in testing docs, and update fix_plan/findings accordingly.
