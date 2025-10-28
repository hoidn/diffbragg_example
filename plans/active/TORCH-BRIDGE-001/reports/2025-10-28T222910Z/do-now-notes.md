# TORCH-BRIDGE-001 Phase A Implementation Notes

**Loop Timestamp:** 2025-10-28T222910Z
**Focus:** TORCH-BRIDGE-001 Phase A — Bridge DataLoad to nanobrag_torch
**Branch:** integration
**Mode:** TDD

## Summary

Successfully implemented Phase A (A1 + A2) of TORCH-BRIDGE-001, delivering a bridge helper that prepares DIALS/simtbx data for nanobrag_torch consumption with full spec-db-core.md compliance.

## Deliverables

### 1. Core Module: `dbex/nanobrag_bridge.py`

**RefinementInputs dataclass:**
- `target`: Background-subtracted [panel, slow, fast] float32 tensor
- `loss_mask`: Boolean mask implementing (background >= 0) ∧ trusted_mask policy
- `panel_slices`: List of (panel_id, bbox) tuples with (x0, x1, y0, y1) format
- `trusted_mask`: Original trusted mask preserving True=include polarity

**prepare_refinement_inputs function:**
- Background subtraction: `target = data - background` where `background >= 0`
- Invalid pixel zeroing: `target[~loss_mask] = 0.0`
- Loss mask policy: `(background >= 0) & trusted_mask` per spec-db-core.md:55
- Array ordering: [panel, slow, fast] per spec-db-core.md:20
- Handles both tuple and array mask inputs (DIALS compatibility)

**Guardrails implemented:**
- Pixel pitch square requirement with explicit error (config_crosswalk.md:30)
- Mask polarity validation (>50% True check) per spec-db-core.md:29
- Shape assertions between data/background/mask arrays
- Explicit error messages citing spec locations

### 2. Test Suite: `tests/dbex/test_nanobrag_bridge.py`

**Fixtures:**
- `mock_detector`: 2-panel square-pixel detector (0.1mm pitch)
- `mock_detector_rectangular`: Non-square pixel detector for guard testing
- `sample_data`: Minimal [2, 512, 512] arrays with 2 ROIs

**Test coverage:**
1. `test_tensor_contract`: Verifies shape, dtype, background subtraction, loss mask policy, panel slices format, and pixel zeroing
2. `test_mask_polarity`: Guards against inverted masks (mostly False)
3. `test_pixel_pitch_guard`: Rejects non-square pixels with clear error
4. `test_tuple_mask_input`: Handles DIALS tuple-of-arrays mask format

## Test Results

**Environment:** `KMP_DUPLICATE_LIB_OK=TRUE` (required for torch compatibility)
**Command:** `python -m pytest -v tests/dbex/test_nanobrag_bridge.py`
**Exit code:** 0
**Runtime:** 0.12s
**Hardware:** CPU (Linux x86_64)

```
collected 4 items

test_tensor_contract ........................... PASSED [ 25%]
test_mask_polarity ............................. PASSED [ 50%]
test_pixel_pitch_guard ......................... PASSED [ 75%]
test_tuple_mask_input .......................... PASSED [100%]

============================== 4 passed in 0.12s
```

## Spec Compliance Checklist

- [x] `[panel, slow, fast]` ordering (spec-db-core.md:20)
- [x] Background subtraction where `background >= 0` (spec-db-core.md:55)
- [x] Loss mask policy: `(background >= 0) & trusted_mask` (spec-db-core.md:55)
- [x] Pixel zeroing where `loss_mask == False`
- [x] ROI bbox format: `(x0, x1, y0, y1)` exclusive upper bounds (spec-db-core.md:22)
- [x] Trusted mask polarity: True=include, 1=include in torch (spec-db-core.md:29, config_crosswalk.md:12)
- [x] Square pixel pitch guard (config_crosswalk.md:30, spec-db-core.md:40)
- [x] Explicit error messages with spec citations

## Phase A Completion Status

### A1 — Fixtures and tensor contract tests ✅
- Mock detector fixtures with square/rectangular variants
- Sample data fixture with 2-panel, 2-ROI setup
- test_tensor_contract validates all output contracts

### A2 — Invariant enforcement ✅
- Pixel pitch guard with threshold 1e-9mm
- Mask polarity guard with 50% True threshold
- Error messages cite spec-db-core.md and config_crosswalk.md

## Next Actions

**Phase B (B1-B2):** Config Hydration
- Map Detector → DetectorConfig (CUSTOM convention, beam center swap)
- Map Beam → BeamConfig (wavelength, polarization)
- Map Crystal → CrystalConfig (unit cell + A* injection)
- Author tests for each config mapping

**Phase C (C1-C2):** Smoke Harness
- Single-experiment end-to-end flow
- Stitch per-panel Bragg tensors
- Compute masked MSE
- Capture ROI triptych artifact

## Findings & Lessons

**Applied:**
- GEOMETRY-001: Pixel pitch guards prevent non-square panel rejection downstream
- CONFORMANCE-001: `KMP_DUPLICATE_LIB_OK=TRUE` required for all torch-adjacent tests

**New:**
- Mask polarity heuristic (>50% True) successfully detects inverted DIALS masks without false positives
- Mock detector fixtures with getitem/iter/len dunder methods work seamlessly with dxtbx Panel API expectations
- NumPy array zeroing via boolean indexing (`target[~mask] = 0.0`) is cleaner than `np.where` chains for readability

## References

- spec-db-core.md:20 — [panel, slow, fast] ordering
- spec-db-core.md:29 — Trusted mask polarity (True=include)
- spec-db-core.md:40 — Square pixel requirement
- spec-db-core.md:55 — Loss mask policy
- config_crosswalk.md:30 — Pixel pitch guard threshold
- dials_api.md:10 — bbox format and reflection alignment
- TESTING_GUIDE.md:6 — KMP_DUPLICATE_LIB_OK requirement

## Artifacts Index

- `pytest.log` — Full pytest output (4 tests, 0.12s)
- `do-now-notes.md` — This document
- `dbex/nanobrag_bridge.py` — Bridge module (132 lines)
- `tests/dbex/test_nanobrag_bridge.py` — Test suite (246 lines)
