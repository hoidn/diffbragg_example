# ARCH-REFINE-FLOW-001 Phase B Blocker

**Date:** 2025-11-23T030000Z
**Phase:** B (Stage A Extraction)
**Status:** BLOCKED (planning/scoping issue)

## Problem Statement

The Phase B Do Now instructs:
- B1: "Implement StageA class wrapping current Stage A parameter initialization, LBFGS closure, and telemetry emission"
- B2: "Update run_nanobrag_refinement to instantiate RefinementEngine([StageA(...)]) when only Stage A is enabled"

This requires extracting ~1000 lines of inline LBFGS closure logic from `run_nanobrag_refinement` (lines 680-1800) into a separate StageA class. However, this extraction is significantly more complex than anticipated because:

1. **Shared state complexity**: The closure accesses ~30 nonlocal variables (config, device, dtype, target_t, loss_mask_t, sigma_readout_t, detector, beam, crystal, hkl_grid, etc.)

2. **Multiple parameterization modes**: The closure branches on 3 different geometry parameterization paths:
   - Default cell+misset path (GEOMETRY-003)
   - U-matrix quaternion path (use_u_matrix_parameterization)
   - Incremental UB path (use_incremental_ub, GEOMETRY-004)

3. **Warm-cache context management**: Stage A uses StageAContext for detector/simulator caching (PERF-WARM-SIM-001) which needs careful coordination

4. **Telemetry complexity**: The closure emits ~15 different telemetry fields, some conditional on config flags

## Attempted Solution

Initial attempt created a StageA class that called `run_nanobrag_refinement`, which would create infinite recursion when run_nanobrag_refinement delegates to the engine.

## Correct Approach (Requires Next Loop)

Per Phase B Do Now pitfall #1: "DO NOT duplicate LBFGS closure — reuse existing functions"

The correct approach is:
1. **Extract helper functions FIRST** (separate loop):
   - `_build_stage_a_params()`: Initialize trainable parameters (lines 761-876)
   - `_build_stage_a_closure()`: Create LBFGS closure with compute_loss nested function (lines 998-1574)
   - `_run_stage_a_lbfgs()`: Execute optimizer.step(closure) and collect telemetry (lines 1575-1700)

2. **Then wrap in StageA.run()** (this loop):
   - Call extracted helpers in sequence
   - Package telemetry with stage_type/mode fields
   - Return dict per RefinementStage protocol

3. **Update run_nanobrag_refinement** (B2):
   - Detect Stage A-only mode (not enable_stage_c)
   - Instantiate RefinementEngine([StageA()])
   - Delegate to engine.run()
   - Keep Stage B/C inline temporarily

## Decision

**STOP Phase B implementation** until extraction helpers are designed and approved.

**Recommended Next Steps:**
1. Supervisor reviews Phase B scope and extraction strategy
2. If approved: Next loop implements helper extraction (B1a)
3. Then: StageA wrapper (B1b)
4. Then: Engine delegation (B2)
5. Then: Validation (B3-B5)

**Estimated Effort:** 3-4 loops total (not 1 loop as originally scoped)

## Baseline Status

✓ B0 complete: Small and full detector baselines recorded
  - `pytest_small.log`: PASSED (18.3% improvement, chi²: 807M → 659M)
  - `pytest_full.log`: PASSED
  - `telemetry_small.json`, `telemetry_full.json`: Captured
  - Test infrastructure bug fixed (nested dict serialization in _record_stage_telemetry)

## Artifacts

- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/`
  - `pytest_collect.log`
  - `pytest_small.log`
  - `pytest_full.log`
  - `telemetry_small.json`
  - `telemetry_full.json`
- `dbex/refinement/stage_a.py` (initial stub, needs rewrite)
- `tests/dbex/test_torch_refine_smoke.py` (fixed param_deltas serialization)

## Code Changes This Loop

1. Fixed telemetry serialization bug (tests/dbex/test_torch_refine_smoke.py:34-53)
   - Added nested list handling for misset_xyz_deg dict values
   - Prevents TypeError when recording Stage A telemetry

2. Created StageA stub (dbex/refinement/stage_a.py)
   - **INCORRECT IMPLEMENTATION** (calls run_nanobrag_refinement, causes recursion)
   - Needs rewrite per extraction strategy above

## Next Actions (Galph)

Review Phase B blocker and provide one of:
- **Path A**: Approve extraction strategy → Ralph implements B1a helper extraction
- **Path B**: Revise scope → Different extraction plan
- **Path C**: Defer Phase B → Focus on different initiative

Do **NOT** proceed with current StageA implementation (recursion bug).
