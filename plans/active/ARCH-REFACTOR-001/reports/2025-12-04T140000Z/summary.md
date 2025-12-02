# ARCH-REFACTOR-001 Phase C.2 — Stage C Helper Inlining

**Date**: 2025-12-04T140000Z
**Agent**: Ralph
**Initiative**: ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation
**Phase**: C.2 — Stage C Helper Inlining

## Objective
Inline `_build_stage_c_params` and `_run_stage_c_lbfgs` from `dbex/refinement/stage_c_impl.py` into the `StageC` class so it owns its LBFGS wiring instead of calling external helpers.

## Changes Made

### 1. `dbex/refinement/stage_c.py` (+605 lines, refactored)
- **Added imports** (lines 22-32): `collections.defaultdict`, `dataclasses.replace`, `json`, `warnings` for Stage C helpers
- **Updated stage_c_impl imports** (lines 37-39): Removed `_build_stage_c_params` and `_run_stage_c_lbfgs`, kept only `_retarget_stage_a_detectors`
- **Added helper imports** (lines 41-49): Imported `_get_sigma_floor_sq_tensor` and `StageAContext` from `stage_a_impl`
- **Created `_build_stage_c_params`** (lines 556-730, 175 lines): Private method that builds Stage C parameters, optimizer, and contexts
  - Returns tuple: `(StageCContext, StageCTelemetryState, param_values dict, optimizer)`
  - Removed legacy compatibility shim for optional kwargs per spec
  - Preserves all warm-cache logic, ROI mode detection, and telemetry initialization
- **Created `_run_lbfgs`** (lines 732-1166, 435 lines): Private method that executes LBFGS optimization
  - Returns tuple: `(stage_result, refinement_telemetry, status, message, bragg_full, param_deltas)`
  - Preserves observer/collector sequencing (baseline validation, LBFGS step, fallback seeding, final validation)
  - Keeps warm-cache detector retargeting via `_retarget_stage_a_detectors`
- **Updated `run` method** (lines 1410-1553):
  - Line 1412: Replaced `_build_stage_c_params(...)` with `self._build_stage_c_params(...)`
  - Lines 1412-1434: Unpacking changed from dict to tuple with typed dataclasses
  - Line 1542: Replaced `_run_stage_c_lbfgs(...)` with `self._run_lbfgs(...)`
  - Lines 1542-1553: Unpacking changed from dict to tuple

### 2. `dbex/refinement/stage_c_impl.py` (-746 lines)
- **Updated module docstring** (lines 1-22): Documented Phase C.2 moves and marked module for deletion in Phase C.3
- **Trimmed imports** (lines 24-38): Removed unused imports (`time`, `math`, `defaultdict`, `Simulator`, `Crystal`, `create_detector_config`, `create_crystal_config`, `_compute_variance_weighted_loss`, `StageCTelemetryState`)
- **Deleted functions** (original lines 224-955):
  - `_build_stage_c_params` (248 lines) → moved to `StageC._build_stage_c_params`
  - `_run_stage_c_lbfgs` (477 lines) → moved to `StageC._run_lbfgs`
- **Retained** (lines 46-208): `_retarget_stage_a_detectors` (will be moved in Phase C.3)

### 3. `dbex/nanobrag_refinement.py` (import cleanup)
- **Lines 70-73**: Updated import comment to reflect Phase C.2; removed `_build_stage_c_params` and `_run_stage_c_lbfgs` from imports

## Testing

### Mapped Selectors (per input.md)
1. **test_stage_b_baseline_guard_diff_payload**
   - Command: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`
   - **Result**: ✅ PASSED (0.91s)
   - Validates Stage B telemetry remains intact after Stage C refactor

2. **test_stage_c_detector_microslip**
   - Command: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small`
   - **Result**: ✅ PASSED (6.95s)
   - Validates Stage C helper inlining preserved REFINE-007/012 behavior

### Results Summary
- All 2/2 mapped tests PASSED
- No telemetry drift or behavioral regression detected
- Stage C now owns its parameter/optimizer construction and LBFGS execution

## Metrics

| Metric | Value |
|--------|-------|
| Files touched | 3 (stage_c.py, stage_c_impl.py, nanobrag_refinement.py) |
| stage_c.py | +605 lines (new private methods), refactored `run()` |
| stage_c_impl.py | -746 lines (deleted 2 functions), trimmed imports |
| nanobrag_refinement.py | -2 imports |
| Net LOC change | ~-140 lines (consolidation via refactoring) |
| Test execution time | 7.86s total (0.91s + 6.95s) |

## Findings Applied
- **ARCH-REFACTOR-001**: Stage helpers must live on their respective Stage classes, not in `_impl.py` modules
- **ARCH-STAGE-CTX-001**: Stage C now uses typed `StageCContext` and `StageCTelemetryState` dataclasses exclusively
- **ARCH-ENGINE-002**: Engine protocol compliance maintained; StageC owns its closures/telemetry
- **ARCH-TELEMETRY-001**: Observer-driven telemetry collection remains the source of truth

## Next Actions
- **Phase C.3** (future): Move `_retarget_stage_a_detectors` into `StageC` and delete `stage_c_impl.py` entirely
- **Immediate**: Update fix_plan.md Attempts History with this loop's summary

## Artifacts
- `pytest_stage_b_guard.log`: Stage B guard test output (PASSED)
- `pytest_stage_c_smoke.log`: Stage C detector microslip smoke test output (PASSED)
- `summary.md`: This document
