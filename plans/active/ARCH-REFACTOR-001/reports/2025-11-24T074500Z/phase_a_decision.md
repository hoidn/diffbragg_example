# ARCH-REFACTOR-001 Phase A Decision

**Date:** 2025-11-24T074500Z
**Loop:** Ralph implementation (i=253)
**Verdict:** PATH A — All tests PASS

## Executive Summary

Phase A code extraction completed successfully. All validation criteria met:
- Phase 0 tests (6 total): 6 PASSED, 0 FAILED
- Regression guards (2 total): 2 PASSED, 0 FAILED

**Next Action:** Mark Phase A checklist complete in implementation.md, proceed to Phase B planning.

## Test Results Summary

### Primary Validation (Phase 0 Tests Against NEW Locations)

**Geometry Tests (tests/dbex/test_geometry_current.py):**
- `test_derive_u_matrix_roundtrip`: PASSED
- `test_derive_u_matrix_edge_case_identity`: PASSED
- Runtime: 0.93s (baseline: 1.05s, -11% improvement)
- Status: ✓ PASS

**Physics Tests (tests/dbex/test_physics_loss_current.py):**
- `test_variance_weighted_loss_basic_clamping`: PASSED
- `test_variance_weighted_loss_zero_mask`: PASSED
- `test_variance_weighted_loss_zero_variance_floor`: PASSED
- `test_variance_weighted_loss_negative_model`: PASSED
- Runtime: 0.83s (baseline: 0.82s, +1% within noise)
- Status: ✓ PASS

### Regression Guards (Production Smoke Tests)

**Stage A Smoke Test (test_stage_a_expansion):**
- Selector: `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Environment: `DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
- Runtime: 12.56s (baseline: 12.61s, -0.4% within noise)
- Status: ✓ PASS

**DB-AT-024 Mapping Parity (test_db_at_024_mapping_smoke):**
- Selector: `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`
- Environment: `DBAT024_ARTIFACT_DIR=plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
- Runtime: 31.68s
- Status: ✓ PASS
- Artifacts: `mapping_metrics.json`, `mapping_metrics.csv` emitted to reports directory

## Code Changes Summary

### New Modules Created

**dbex/geometry/crystallography.py (121 lines)**
- Function: `derive_u_matrix_from_mosflm_a_star(a_star, cell) -> (U, B_ideal)`
- Dependencies: numpy, torch, nanobrag_torch.config, nanobrag_torch.models.crystal
- Leaf-node constraint: ✓ SATISFIED (no imports from dbex.nanobrag_*)
- Spec compliance: GEOMETRY-004, preserves strain per docs/spec-db-workflow.md

**dbex/physics/loss.py (55 lines)**
- Function: `_compute_variance_weighted_loss(bragg_tensor, target_tensor, loss_mask, sigma_tensor, sigma_floor_sq_tensor) -> (chi_sq, mse, n_pixels, n_clamped)`
- Dependencies: torch
- Leaf-node constraint: ✓ SATISFIED (no imports from dbex.nanobrag_*)
- Spec compliance: docs/spec-db-core.md:57-80 (V = I_model + sigma^2 detachment preserved)

### Import Updates

**dbex/nanobrag_bridge.py:801-802**
- Removed: `derive_u_matrix_from_mosflm_a_star` function definition (94 lines)
- Added: `from dbex.geometry.crystallography import derive_u_matrix_from_mosflm_a_star`

**dbex/nanobrag_refinement.py:447-448**
- Removed: `_compute_variance_weighted_loss` function definition (34 lines)
- Added: `from dbex.physics.loss import _compute_variance_weighted_loss`

## Metrics

- **Lines extracted:** 128 (94 geometry + 34 physics)
- **Lines replaced:** 128 (deleted) + 4 (import statements) = -124 net in original modules
- **New modules:** 2 (crystallography.py, loss.py)
- **Test coverage:** 6 tests cover extracted functions (100% of Phase 0 coverage)
- **No logic changes:** ✓ CONFIRMED (pure code movement, signatures unchanged)
- **No gradient flow changes:** ✓ CONFIRMED (no .detach() added/removed)

## Validation Evidence

### Leaf-Node Constraint Verification

**dbex/geometry/crystallography.py:**
```python
# Imports FROM external dependencies only
from nanobrag_torch.config import CrystalConfig as TorchCrystalConfig
from nanobrag_torch.models.crystal import Crystal as TorchCrystal
import torch
```
✓ No imports from dbex.nanobrag_* (leaf-node compliant)

**dbex/physics/loss.py:**
```python
# Imports FROM external dependencies only
import torch
```
✓ No imports from dbex.nanobrag_* (leaf-node compliant)

### Spec Compliance

**PHYSICS-LOSS-001 (Variance Formula):**
- docs/spec-db-core.md:57-80 requires V = max(I_model + sigma², variance_floor²)
- Implementation in dbex/physics/loss.py:30-31:
  ```python
  variance_raw = bragg_tensor.detach() + sigma_tensor ** 2
  variance = torch.maximum(variance_raw, sigma_floor_sq_tensor)
  ```
- ✓ PRESERVED (exact code movement, no changes)

**GEOMETRY-003 (B_ideal Convention):**
- docs/config_crosswalk.md requires MOSFLM A* = U @ B_ideal reconstruction
- Implementation in dbex/geometry/crystallography.py:92-113:
  ```python
  U = a_star @ B_inv  # A* = U @ B_ideal => U = A* @ inv(B_ideal)
  ```
- ✓ PRESERVED (exact code movement, no changes)

## Findings Applied

- **POLICY-001:** Environment Freeze (no package installs, code movement only) ✓
- **PHYSICS-LOSS-001:** Variance formula preserved ✓
- **GEOMETRY-003:** B_ideal convention preserved ✓
- **GRADIENT-001:** Autograd graph preservation (no .detach() changes) ✓
- **REFINE-001:** LBFGS behavior validated via Stage A smoke test ✓

## Phase A Checklist Status

From `plans/active/ARCH-REFACTOR-001/implementation.md:92-106`:

- [x] A1: Create `dbex/geometry/crystallography.py` — ✓ COMPLETE (2025-11-24T074500Z)
- [ ] A2: Create `dbex/geometry/rotations.py` — DEFERRED (no Phase 0 tests, low priority)
- [x] A3: Create `dbex/physics/loss.py` — ✓ COMPLETE (2025-11-24T074500Z)
- [x] A4: Update imports in `nanobrag_bridge.py` and `nanobrag_refinement.py` — ✓ COMPLETE (2025-11-24T074500Z)

**Phase A Status:** ✓ COMPLETE (2025-11-24T074500Z)

## Artifacts

All artifacts saved to `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/`:
- `phase_a_planning_analysis.md` (planning document)
- `pytest_geometry_new.log` (2 tests PASSED, 0.93s)
- `pytest_physics_new.log` (4 tests PASSED, 0.83s)
- `regression_stage_a.log` (1 test PASSED, 12.56s)
- `regression_db_at_024.log` (1 test PASSED, 31.68s)
- `phase_a_decision.md` (this document)
- `mapping_metrics.json` (DB-AT-024 parity metrics)
- `mapping_metrics.csv` (per-ROI correlation data)

## Next Actions

1. Update `plans/active/ARCH-REFACTOR-001/implementation.md` Phase A checklist (mark A1, A3, A4 complete)
2. Commit Phase A changes with message: "ARCH-REFACTOR-001 Phase A: Physics extraction (derive_u_matrix, variance_weighted_loss) — tests: run"
3. Return to Galph for Phase B planning (telemetry standardization)

## Confidence Assessment

**HIGH confidence** Phase A succeeded as predicted in planning analysis:
- Pure code movement (no logic changes) minimized risk
- Phase 0 safety net caught any breakage immediately
- Leaf-node constraint prevented circular imports
- Regression guards protected production behavior
- All 8 tests passed (6 Phase 0 + 2 regression guards)

Phase A runtime: ~45 minutes (faster than 3-4 hour estimate, no debugging required)
