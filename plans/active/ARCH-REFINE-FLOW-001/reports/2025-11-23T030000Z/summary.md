# ARCH-REFINE-FLOW-001 Phase B0 Summary

**Date:** 2025-11-23T030000Z
**Phase:** B0 (Baseline Recording) + Test Infrastructure Fix
**Status:** COMPLETE (B0) / BLOCKED (B1-B5)
**Loop ID:** 2025-11-23T030000Z

## Overview

Executed Phase B0 baseline artifact collection per input.md. Discovered and fixed test infrastructure bug preventing telemetry serialization. Identified Phase B extraction complexity requires supervisor scope review before proceeding with B1-B5.

## Deliverables (B0)

✓ **Baseline Artifacts Recorded**
- Collection log: `pytest_collect.log` (1 test collected)
- Small detector: `pytest_small.log` (PASSED, 18.3% improvement, chi²: 807M → 659M)
- Full detector: `pytest_full.log` (PASSED)
- Telemetry: `telemetry_small.json`, `telemetry_full.json`

✓ **Test Infrastructure Fix**
- Fixed nested dict serialization in `_record_stage_telemetry` (tests/dbex/test_torch_refine_smoke.py:34-53)
- Added nested list handling for `misset_xyz_deg` dict values (`{'initial': [x,y,z], 'final': [x,y,z], 'quaternion_norm': float}`)
- Prevents `TypeError: float() argument must be a string or a number, not 'list'`

## Blocker (B1-B5)

Phase B extraction requires clarifying extraction strategy due to:
1. ~1000 lines of inline LBFGS closure logic in `run_nanobrag_refinement`
2. 30+ nonlocal variables accessed by closure
3. 3 geometry parameterization modes (cell+misset, U-matrix, incremental UB)
4. Warm-cache context management (StageAContext)
5. Conditional telemetry fields

**Conflicting Requirements:**
- Do Now B1: "Reuse existing `build_stage_a_lbfgs_closure` and `run_lbfgs_optimization`" (functions don't exist)
- Pitfall #1: "DO NOT duplicate LBFGS closure"
- Goal: Extract Stage A logic WITHOUT duplication

**Recommended Path:** Multi-loop extraction (3-4 loops):
1. B1a: Extract helper functions (`_build_stage_a_params`, `_build_stage_a_closure`, `_run_stage_a_lbfgs`)
2. B1b: Wrap helpers in StageA class
3. B2: Update `run_nanobrag_refinement` to delegate to engine
4. B3-B5: Validation + docs

See `phase_b_blocker.md` for full analysis.

## Code Changes

### 1. Test Infrastructure Fix (tests/dbex/test_torch_refine_smoke.py)

**File:** `tests/dbex/test_torch_refine_smoke.py:34-53`

**Change:** Added nested list handling in param_deltas serialization

```python
# Before (lines 40-43):
param_deltas_serialized[key] = {
    k: float(v) if hasattr(v, 'item') else float(v)
    for k, v in value.items()
}

# After (lines 40-47):
param_deltas_serialized[key] = {}
for k, v in value.items():
    if isinstance(v, (list, tuple)):
        # Nested list within dict (e.g., misset_xyz_deg initial/final)
        param_deltas_serialized[key][k] = [float(x) if hasattr(x, 'item') else float(x) for x in v]
    else:
        # Scalar within dict
        param_deltas_serialized[key][k] = float(v) if hasattr(v, 'item') else float(v)
```

**Rationale:** `misset_xyz_deg` telemetry field is a nested dict with list values: `{'initial': [x,y,z], 'final': [x,y,z], 'quaternion_norm': float}`. Previous logic assumed all nested dict values were scalars, causing TypeError when trying to convert lists to float.

**Validation:** Both small and full detector smoke tests now PASS with telemetry serialization working correctly.

### 2. StageA Stub (dbex/refinement/stage_a.py)

**File:** `dbex/refinement/stage_a.py` (new file, 150 lines)

**Status:** **INCORRECT IMPLEMENTATION** (causes recursion)

**Issue:** `StageA.run()` calls `run_nanobrag_refinement`, which per B2 should call `RefinementEngine([StageA()])`, creating infinite recursion.

**Action:** DO NOT USE this implementation. Needs rewrite per extraction strategy.

### 3. Package Export (dbex/refinement/__init__.py)

**Change:** Added `StageA` to `__all__` exports (line 32-34)

**Status:** Export works but implementation is broken (see #2 above)

## Artifacts Index

**Reports Root:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/`

**Baseline Directory:** `baseline/`
- `pytest_collect.log` — Collection verification (1 test)
- `pytest_small.log` — Small detector baseline (PASSED)
- `pytest_full.log` — Full detector baseline (PASSED)
- `telemetry_small.json` — Small detector telemetry
- `telemetry_full.json` — Full detector telemetry

**Planning Documents:**
- `phase_b_blocker.md` — Extraction complexity analysis + recommended path
- `summary.md` — This file

## Metrics

**Baseline Test Results:**
- **Small Detector:**
  - Status: PASSED
  - Initial chi²: 8.07e+08
  - Final chi²: 6.59e+08
  - Improvement: 18.3%
  - Iterations: 30
  - Runtime: 12.48s

- **Full Detector:**
  - Status: PASSED
  - (Full metrics in telemetry_full.json)

**Test Infrastructure:**
- Bug: Nested dict serialization failure
- Fix: 14 lines changed (tests/dbex/test_torch_refine_smoke.py:40-53)
- Validation: Both smoke tests PASS

## Next Actions (Supervisor)

**Decision Required:** Review `phase_b_blocker.md` and select path:
- **Path A**: Approve multi-loop extraction strategy → Ralph implements B1a (helper extraction)
- **Path B**: Revise extraction plan → New Do Now for B1
- **Path C**: Defer Phase B → Focus on different initiative

**DO NOT:** Proceed with current `dbex/refinement/stage_a.py` (recursion bug).

**Dependencies:** Phase B1-B5 blocked until supervisor provides extraction strategy.

## Exit Criteria Status

**Phase B0:**
- ✓ Baseline artifacts recorded (small + full detector)
- ✓ Test infrastructure bug fixed
- ✓ Artifacts archived under reports directory

**Phase B1-B5:** BLOCKED (scope clarification needed)

## Compliance

**Spec Alignment:**
- docs/spec-db-workflow.md:33 (Engine Contract) — Phase A complete, Phase B pending
- docs/spec-db-tracing.md §2 (telemetry) — Telemetry schema extended in Phase A, baseline validates structure

**Findings Applied:**
- REFINE-005/006 (Stage A gates) — Baseline validates ≥0.2% improvement
- PERF-WARM-SIM-001 (warm cache) — Baseline confirms cache_mode="warm" in telemetry
- GEOMETRY-004 (incremental UB) — Not exercised in baseline (use_incremental_ub=False)
- POLICY-001 (Environment Freeze) — No package modifications

## Lessons Learned

1. **Nested telemetry serialization:** When extending telemetry schema with nested structures (Phase A4), ensure test infrastructure handles all nesting levels (dicts, lists, nested dicts with lists).

2. **Extraction planning:** Large inline code blocks (~1000 lines) require multi-loop extraction strategy, not single-loop wrapper. Attempting direct wrapper leads to recursion bugs.

3. **Do Now ambiguity:** "Reuse existing functions" should clarify whether functions exist or need to be created as part of the task.


### Turn Summary
Recorded Stage A baseline artifacts for small and full detectors (both PASSED, 18.3% improvement on small).
Fixed test infrastructure bug where nested dicts with list values failed telemetry serialization (misset_xyz_deg field).
Phase B1-B5 blocked: attempted StageA extraction causes recursion; recommended multi-loop helper extraction strategy documented in phase_b_blocker.md.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/ (telemetry_small.json, pytest_small.log, pytest_full.log)
