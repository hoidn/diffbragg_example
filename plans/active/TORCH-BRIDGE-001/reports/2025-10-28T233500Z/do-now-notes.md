# Do Now Notes: TORCH-BRIDGE-001 Closure Run
## Timestamp: 2025-10-28T233500Z

## Summary
Final validation run for TORCH-BRIDGE-001 to confirm all bridge and smoke tests pass before marking initiative complete.

## Actions Taken
1. Verified `refGeom.refl` dataset exists (205852 bytes).
2. Created artifact directory: `plans/active/TORCH-BRIDGE-001/reports/2025-10-28T233500Z/`.
3. Captured runtime environment (Python 3.9.23, PyTorch 2.8.0).
4. Executed test suite with `KMP_DUPLICATE_LIB_OK=TRUE` environment flag.
5. Copied smoke metrics and ROI triptych artifacts from previous run (2025-10-28T230500Z).

## Test Results
**Command:**
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py
```

**Outcome:** ✅ All 21 tests PASSED
- Bridge tests (4/4): Tensor contract, mask polarity, pixel pitch guard, tuple mask input
- Config tests (14/14): Detector, beam, crystal config hydration and mapping
- Smoke tests (3/3): Single experiment flow, masked MSE computation, artifact generation

**Runtime:** 1.93s (CPU)
**Warnings:** 4 deprecation warnings (SWIG, pkg_resources) - non-blocking

## Artifacts Summary
- `pytest.log`: Full test output (21 passed, 4 warnings)
- `run_env.txt`: Python 3.9.23 + PyTorch 2.8.0 version info
- `smoke_metrics.json`: Metrics from smoke harness (copied from 2025-10-28T230500Z)
  - n_rois: 92
  - target_shape: [1, 2527, 2463]
  - masked_mse: 959991.3 (stub Gaussian vs real data baseline)
  - loss_mask_coverage: 0.21%
- `roi_triptych.png`: Visual artifact showing ROI layout (copied from 2025-10-28T230500Z)

## Spec Compliance Verified
- **[panel, slow, fast] ordering** (docs/spec-db-core.md:24) — ✅ Validated by tensor contract test
- **Square pixel guard** (docs/spec-db-core.md:43) — ✅ Pixel pitch guard test passes
- **Detector/beam/crystal mapping** (docs/config_crosswalk.md:16-34) — ✅ All 14 config tests pass
- **Masked MSE harness** (docs/spec-db-workflow.md:24-29) — ✅ Smoke tests exercise full flow
- **Geometry extraction via dxtbx** (docs/dxtbx_api.md:5-42) — ✅ Config hydration tests validate

## Dataset Requirements
- **refGeom.refl:** ✅ Present (205852 bytes)
- **refGeom.expt:** ✅ Loaded by smoke tests
- **scaled.mtz:** ✅ Structure factors loaded successfully
- **Images:** ✅ CBF files read via simtbx/dxtbx

No tests skipped due to missing datasets.

## Exit Criteria Status
All Phase C exit criteria from TORCH-BRIDGE-001 implementation plan met:

1. ✅ Helper returns background-subtracted targets, trusted/background masks, per-panel slices aligned to `[panel, slow, fast]`
2. ✅ Detector/beam/crystal configs hydrate the torch simulator (stubbed)
3. ✅ Bridge raises when pixel pitch is not square
4. ✅ Smoke harness exercises one DIALS experiment with ROI triptych artifact

## Next Actions
1. Update `docs/fix_plan.md` status → `done` with this Attempts History entry
2. Archive implementation plan at `plans/active/TORCH-BRIDGE-001/implementation.md`
3. Initiative ready for handoff to TORCH-RUNTIME-002 or TORCH-CLI-003

## Notes
- Stub simulator (`stub_bragg_tensor`) remains in place pending `nanobrag_torch` installation
- Crystal A* tuple→array pattern handled correctly (see test_mosflm_astar_injection)
- No findings requiring `docs/findings.md` update discovered in this closure run
