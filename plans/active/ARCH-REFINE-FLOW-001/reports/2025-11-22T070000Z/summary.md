### Turn Summary
Extracted _run_stage_b_lbfgs helper (~118 lines LBFGS execution + improvement gate), fixed helper2 signature bug (return tuple not scalar), wired all 3 helpers into run_nanobrag_refinement (~610 lines → ~150 lines orchestration), fixed 5 critical bugs (panel_slices, key mismatches, nanobrag_torch imports), regression guard test_stage_b_shell_modifiers PASSED.
Phase C1a COMPLETE (3-loop multi-stage extraction strategy SUCCESS per Phase B precedent).
Next: Phase C1b (StageB wrapper class calling extracted helpers).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/ (pytest log, patch 794 lines)

---

# Phase C1a-loop3 Implementation Summary

## Objective
Extract `_run_stage_b_lbfgs` helper (~100 lines), fix helper2 signature bug, wire all 3 Stage B helpers into `run_nanobrag_refinement`, and run MANDATORY regression guard.

## Deliverables

### 1. Helper3: `_run_stage_b_lbfgs` Extraction
- **Location**: dbex/nanobrag_refinement.py:2593-2708 (~118 lines)
- **Signature**: `_run_stage_b_lbfgs(config, device, dtype, param_values, closure_stage_b, compute_loss_stage_b, n_panels) -> Dict[str, Any]`
- **Extracted Logic**:
  - Initial full validation (TORCH-REFINE-004 mandatory check)
  - LBFGS optimizer.step() execution
  - Exception handling
  - Final validation + best snapshot restore
  - Improvement gate check (REFINE-008)
- **Returns**: Dict with status, message, final_loss_value, final_mse_value, plus best metric tuples

### 2. Helper2 Signature Bugfix
- **Issue**: Helper2 originally returned only `closure_stage_b`, but helper3 needs BOTH `compute_loss_stage_b` AND `closure_stage_b` for final validation
- **Fix Applied** (line 2590):
  ```python
  return compute_loss_stage_b, closure_stage_b  # Was: return closure_stage_b
  ```
- **Signature Updated** (line 2299):
  ```python
  ) -> Tuple[Callable[[List[int], bool, bool], Tuple[torch.Tensor, torch.Tensor]], Callable[[], torch.Tensor]]:
  ```

### 3. Critical Bugfixes During Wiring

#### Bug 1: Missing `panel_slices` Assignment
- **Error**: `NameError: name 'panel_slices' is not defined` (line 3211)
- **Root Cause**: Subagent wiring removed the `panel_slices = inputs.panel_slices` assignment
- **Fix** (line 2875): Added back assignment in run_nanobrag_refinement function scope

#### Bug 2: Key Mismatch in param_values Dict
- **Error**: `KeyError: 'stage_b_params'`
- **Root Cause**: Helper1 returns `'params'` key but wiring expected `'stage_b_params'`
- **Fixes Applied**:
  1. Helper2 param extraction (line 2320): Changed `stage_b_params = param_values['stage_b_params']` → `stage_b_params = param_values['params']`
  2. Wiring code (line 3231): Same fix
  3. Added `'stage_b_param_device'` to helper1 return dict (line 2269)

#### Bug 3: Telemetry Nested Access
- **Root Cause**: Helper1 returns telemetry items inside `'telemetry_state'` dict, but wiring/helpers accessed them directly
- **Fixes Applied**:
  1. Helper2 (lines 2323-2338): Added `telemetry = param_values['telemetry_state']` and extracted all telemetry items via nested access
  2. Helper3 (lines 2614-2619): Same nested access pattern
  3. Wiring code (lines 3294-3305): Same nested access pattern

#### Bug 4: Incorrect nanobrag_torch Imports
- **Error**: `ImportError: cannot import name 'Detector' from 'nanobrag_torch'`
- **Root Cause**: Classes moved to submodules in nanobrag_torch structure
- **Fix** (line 2357-2358):
  ```python
  from nanobrag_torch.models import Detector, Crystal  # Was: from nanobrag_torch import Detector, Crystal, Simulator
  from nanobrag_torch.simulator import Simulator
  ```

#### Bug 5: Helper3 Return Dict Incomplete
- **Fix** (lines 2701-2709): Added all required keys to return dict including best metric tuples

### 4. Stage B Helper Orchestration Wiring
- **Code Replaced**: Lines 3152-3609 (~458 lines of inline Stage B code)
- **Code After Refactoring**: Lines 3152-3302 (~151 lines of helper orchestration)
- **Net Reduction**: ~307 lines removed from run_nanobrag_refinement
- **Pattern**:
  1. Call `_build_stage_b_params` (helper1) to build parameters, optimizer, telemetry accumulators
  2. Add frozen Stage A tensors to param_values (log_scale, 6 cell tensors, misset_xyz_deg, best_loss_full)
  3. Call `_build_stage_b_lbfgs_closure` (helper2) to build closure functions (returns tuple)
  4. Call `_run_stage_b_lbfgs` (helper3) to execute LBFGS optimization
  5. Unpack results and extract telemetry accumulators (updated in-place by closures)
  6. Keep final Bragg generation code AS-IS (lines 3304-3453)

### 5. Regression Guard Validation
- **Test**: `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
- **Environment**: `DBEX_SMOKE_DETECTOR_SIZE=small`, `DBEX_SMOKE_SIGMA_SOURCE=cli_override`, `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`
- **Result**: PASSED (exit code 0)
- **Runtime**: ~14.7s
- **Log**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/pytest_stage_b_shell_modifiers.log

## Compilation Check
- **Command**: `python -c "import dbex.nanobrag_refinement"`
- **Result**: SUCCESS (exit code 0)
- **Log**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/compilation_check.log

## Findings Applied
- **REFINE-008**: Stage B calibrated gate ≥0.002% improvement check implemented in helper3
- **PERF-WARM-009**: Force panel evaluation for initial/final Stage B validations
- **PERF-WARM-011/012**: CPU fallback logic preserved in helper1 and helper2
- **PHYSICS-LOSS-001/002**: Dual metric tracking (chi_squared + masked_mse) maintained
- **POLICY-001**: Environment Freeze — no new packages installed, targeted import fixes only

## Phase C1a Completion Status
- ✅ C1a-loop1: Extract `_build_stage_b_params` (2025-11-22T060833Z)
- ✅ C1a-loop2: Extract `_build_stage_b_lbfgs_closure` (2025-11-22T063000Z)
- ✅ C1a-loop3: Extract `_run_stage_b_lbfgs` + wire all 3 helpers + regression guard (2025-11-22T070000Z)

**Phase C1a is now COMPLETE.** All 3 helpers extracted (~600+ lines total), wired into run_nanobrag_refinement, 5 critical bugs fixed, and regression guard PASSED.

## Metrics
- **Total helper lines**: ~600+ (helper1: ~184, helper2: ~317, helper3: ~118)
- **Inline code replaced**: ~458 lines
- **Orchestration code**: ~151 lines
- **Net reduction**: ~307 lines in run_nanobrag_refinement
- **Patch size**: 794 lines (additions + deletions + context)
- **Compilation**: PASSED
- **Regression guard**: PASSED

## Next Steps
**Phase C1b** (next loop):
- Implement StageB wrapper class (dbex/refinement/stage_b.py)
- StageB.run() calls 3 extracted helpers directly (mirroring Phase B1b pattern)
- Package telemetry with RefinementTelemetry fields + stage_type="B" + mode="shell_modifiers"
- Regression guard: test_stage_b_shell_modifiers MUST PASS
- Engine contract test: test_engine_executes_mock_stage with StageB stub

## Artifacts
- `phase_c1a_loop3_extraction_diff.patch` (794 lines)
- `compilation_check.log` (PASSED)
- `pytest_stage_b_shell_modifiers.log` (PASSED, 14.7s)
- `summary.md` (this file)
