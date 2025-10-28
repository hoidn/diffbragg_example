# Phase C Smoke Harness — Do Now Completion

**Date:** 2025-10-28T230500Z
**Focus:** TORCH-BRIDGE-001.C — Bridge DataLoad to nanobrag_torch
**Mode:** TDD
**Branch:** integration

## Summary

Successfully implemented Phase C smoke harness per `input.md` checklist C1-C2. All tests pass with KMP_DUPLICATE_LIB_OK=TRUE.

## Deliverables

### C1: Smoke Harness Test Scaffold

**Module:** `tests/dbex/test_nanobrag_smoke.py`

Authored pytest harness exercising:
1. DataLoad → bridge → stub simulator flow
2. RefinementInputs preparation via `prepare_refinement_inputs`
3. Config hydration: DetectorConfig, BeamConfig, CrystalConfig
4. Stitched Bragg tensor in `[panel, slow, fast]` ordering
5. Masked MSE computation per spec-db-workflow.md:28

**Tests:**
- `TestSmokeHarness::test_single_experiment_flow` — validates end-to-end flow
- `TestSmokeHarness::test_masked_mse_and_shapes` — validates metrics and tensor contracts
- `test_artifact_generation` — validates artifact persistence

### C2: Artifacts and Metrics

**Location:** `plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/`

**Files:**
- `smoke_metrics.json` (328 bytes) — masked MSE, intensity stats, coverage
- `roi_triptych.png` (66 KB) — data/model/residual visualization for ROI 0
- `pytest.log` (32 KB) — test execution log

**Metrics:**
- **n_panels:** 1
- **n_rois:** 92
- **target_shape:** [1, 2527, 2463]
- **bragg_shape:** [1, 2527, 2463]
- **masked_mse:** 959991.3125 (stub Gaussian vs real data)
- **mean_intensity_per_panel:** [98.89] ADU
- **max_intensity_per_panel:** [473.20] ADU
- **loss_mask_coverage:** 0.21% (valid ROI pixels)

## Implementation Notes

### Data Preparation

- Generated `refGeom.refl` via `dials.stills_process` (per README.md Step 5)
- Updated `refGeom.expt` image path to local CBF file (was absolute path)
- MTZ column corrected to `"F,SIGF"` (available columns discovered at runtime)

### Bridge Fixes

1. **Crystal A* matrix parsing** (`dbex/nanobrag_bridge.py:370`):
   - `crystal.get_A()` returns 9-element tuple (row-major), not numpy array
   - Fixed by reshaping: `A = np.array(A_tuple).reshape(3, 3)`

2. **Trusted mask construction** (test fixtures):
   - dxtbx Detector has no `get_untrusted_rectangle_mask()` method
   - Built masks manually from panel.get_mask() rectangle definitions
   - Rectangles mark *untrusted* regions; inverted to True=trusted polarity

### Test Coverage

All three tests pass (3/3, 1.83s runtime, CPU):

```
tests/dbex/test_nanobrag_smoke.py::TestSmokeHarness::test_single_experiment_flow PASSED
tests/dbex/test_nanobrag_smoke.py::TestSmokeHarness::test_masked_mse_and_shapes PASSED
tests/dbex/test_nanobrag_smoke.py::test_artifact_generation PASSED
```

**Environment:**
- `KMP_DUPLICATE_LIB_OK=TRUE` (per CONFORMANCE-001)
- Python 3.9.23, pytest 8.4.2
- Platform: linux, CPU-only (stub simulator)

## Spec Compliance

- ✅ [panel, slow, fast] ordering (spec-db-core.md:20)
- ✅ Loss mask: (background >= 0) ∧ trusted (spec-db-core.md:55)
- ✅ Masked MSE: mean((Bragg - target)[loss_mask]²) (spec-db-workflow.md:28)
- ✅ Per-panel config hydration (config_crosswalk.md, dxtbx_api.md)
- ✅ ROI triptych artifact with axis labels (config_crosswalk.md:86-95)

## Findings Applied

- **GEOMETRY-001:** Square pixel guard enforced in `prepare_refinement_inputs`
- **CONFORMANCE-001:** KMP_DUPLICATE_LIB_OK=TRUE exported before pytest
- **RUNTIME-001:** torch.compile disabled (N/A for stub harness, noted for future)

## Next Actions

1. Phase C complete; mark C1/C2 checkboxes in `implementation.md`
2. Update `fix_plan.md` Attempts History with metrics/artifacts
3. Consider authoring new finding for crystal A* tuple vs array discrepancy
4. When `nanobrag_torch` is available, replace stub_bragg_tensor fixture with real simulator invocation

## Blockers / Deviations

None. All exit criteria met.

---

**Signed off:** 2025-10-28T231200Z
