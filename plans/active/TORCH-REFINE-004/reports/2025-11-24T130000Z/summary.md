# Phase 6 ASU Mapping Implementation Summary

**Date:** 2025-11-24T130000Z

**Initiative:** TORCH-REFINE-004 (Stage B Per-Reflection Mode Migration)

**Mode:** TDD (Test-Driven Development)

**Objective:** Implement per-reflection Fhkl modifier parameterization infrastructure with ASU (asymmetric unit) index mapping for Stage B.

## Deliverables Shipped

### 1. Helper Functions (dbex/nanobrag_refinement.py:239-447)

**compute_hkl_asu_map** (lines 239-357)
- Maps HKL grid voxels to unique ASU indices using cctbx.miller symmetry operations
- Inputs: hkl_grid (numpy), crystal_symmetry (from MTZ), optional halo_mask
- Outputs: (hkl_asu_map torch.Tensor[int64], n_asu_unique int) or (None, 0) on failure
- Edge cases handled: Halo voxels (map to index 0), Friedel pairs (anomalous_flag=False), symmetry failures (fallback to shell mode)
- Lazy imports cctbx (ARCH-ENGINE-002) for optional dependency handling

**initialize_asu_modifiers** (lines 360-407)
- Initializes log-space per-reflection modifiers as nn.Parameter
- Fixed halo modifier at index 0 (log(1.0) = 0.0) with gradient hook
- Hook implementation: clones gradient and zeros index 0 to prevent training halo modifier

**apply_asu_modifiers** (lines 410-447)
- Applies per-reflection ASU modifiers to HKL grid structure factors
- Clamps log_modifiers to [-3, 3] range (linear modifiers ∈ [0.05, 20.1])
- Broadcast via index lookup: modifier_grid = modifiers[hkl_asu_map]
- Element-wise multiplication: hkl_grid_modified = hkl_grid_base * modifier_grid

### 2. Configuration Fields (dbex/nanobrag_refinement.py:520-523)

Extended RefinementConfig with 3 new fields for ASU mode:
- stage_b_optimizer_gate: int = 10000 — n_asu threshold for LBFGS vs Adam selection
- stage_b_adam_lr: float = 1e-3 — Adam learning rate for large parameter counts (≥10K)
- stage_b_modifier_clamp: Tuple[float, float] = (-3.0, 3.0) — log-space clamp range

### 3. Unit Tests (tests/dbex/test_stage_b_asu_mapping.py)

Created comprehensive test suite (252 lines, 5 tests, ALL PASSED):
- test_asu_mapping_p1: Validates P1 space group with Friedel pair folding (63 unique ASU from 125 voxels)
- test_asu_mapping_p432: Validates P432 high-symmetry (56 unique ASU from 1331 voxels, ~1/48 reduction)
- test_asu_halo_handling: Validates halo voxels map to ASU index 0, gradient hook zeros halo modifier
- test_asu_friedel_pairs: Validates (h,k,l) and (-h,-k,-l) map to same ASU index (anomalous_flag=False)
- test_apply_asu_modifiers: Validates correct element-wise multiplication and log-space clamping

Test Results: 5 passed in 1.06s (runtime < 10s per Phase 6 scope)

## Phase 6 Exit Criteria: 6/7 COMPLETE

✅ compute_hkl_asu_map helper implemented
✅ initialize_asu_modifiers helper implemented
✅ apply_asu_modifiers helper implemented
✅ RefinementConfig extended with ASU fields
✅ Unit tests created (P1, P432, halo, Friedel)
✅ Unit tests runtime < 10s
❌ Shell mode regression guard FAILED (unrelated engine telemetry_version schema mismatch)

## Blocker Identified

**Engine telemetry_version schema mismatch (BLOCKS Phase 7)**
- Error: TypeError: __init__() got an unexpected keyword argument 'telemetry_version'
- Location: dbex/refinement/engine.py:144
- Not caused by Phase 6 (pure helper functions + config fields, no engine integration)
- Must be fixed before Phase 7 optimization loop integration

## Next Phase

Phase 7 (Optimization Loop Integration) — after engine schema fix:
- Integrate apply_asu_modifiers into Stage B optimization closure
- Dynamic optimizer selection (LBFGS < 10K, Adam ≥ 10K)
- Integration smoke test (P1 fixture, ~35K parameters, Adam)
- Estimated effort: 1 loop (~2 hours) after schema fix
