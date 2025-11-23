# ARCH-REFINE-FLOW-001 Phase B1a-loop2 — Extract `_build_stage_a_lbfgs_closure` Helper ONLY

## Summary
Extract ONLY the second helper function (`_build_stage_a_lbfgs_closure`) with TWO nested functions (compute_loss + closure) from inline code in `run_nanobrag_refinement`. This is loop 2 of 3 for Phase B1a extraction (approved multi-loop strategy).

## Mode
none (incremental production refactoring, partial progress commit)

## Focus
ARCH-REFINE-FLOW-001 — Refactor to Protocol-based Refinement Engine (Phase B1a-loop2: Extract second helper with nested functions)

## Branch
integration

## Mapped Tests
- **NONE** — This loop extracts a helper but does NOT wire it into the runtime (no regression guard needed)
- **Compilation verification only:** Ensure imports/syntax are valid after extraction

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/`
- `helper2_extraction_summary.md` (MANDATORY — extraction notes, line ranges, nonlocal variable list)
- `compilation_check.log` (MANDATORY — python -m py_compile dbex/nanobrag_refinement.py output)
- `summary.md` (MANDATORY — Turn Summary block)

## Do Now (Simplified — Extract Helper 2 ONLY)

### Context
This is **loop 2 of 3** for Phase B1a helper extraction. Loop 1 (i=192) successfully extracted `_build_stage_a_params` helper (~328 lines). This loop extracts the more complex `_build_stage_a_lbfgs_closure` helper with TWO nested functions requiring lexical scope preservation for ~30 nonlocal variables.

**Scope:**
- **This loop (i=193):** Extract `_build_stage_a_lbfgs_closure` ONLY (~584 lines: lines 1320-1903 with nested compute_loss + closure)
- **Next loop (i=194):** Extract `_run_stage_a_lbfgs` + refactor main function + regression guard

### Step 1: Review Helper 1
Read helper 1 extraction summary to understand return structure:
```bash
cat plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/helper1_extraction_summary.md
```

Helper 1 returns Dict with keys: `params`, `param_values`, `telemetry_state`, `stage_a_context`, `optimizer`

### Step 2: Extract `_build_stage_a_lbfgs_closure` Helper

**Location:** Add AFTER `_build_stage_a_params` in `dbex/nanobrag_refinement.py` (after line 1007)

**Action:** Copy lines 1320-1903 from `run_nanobrag_refinement` (includes telemetry_step_counter setup through closure return statement) into this new helper function.

**Exact Signature:**
```python
def _build_stage_a_lbfgs_closure(
    # Parameters from helper 1 return dict
    param_values: Dict[str, torch.Tensor],
    telemetry_state: Dict[str, Any],
    stage_a_context: Dict[str, Any],
    # Additional closure context (11 params)
    crystal,
    detector,
    beam,
    inputs,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config: RefinementConfig,
    sigma_floor_sq_cache: Optional[torch.Tensor],
    device,
    dtype,
    baseline_crystal
) -> Tuple[Callable, Callable]:
    """
    Build LBFGS closure for Stage A refinement with nested compute_loss and closure functions.

    Captures lexical scope for ~30 nonlocal variables from param_values, telemetry_state, stage_a_context.
    Supports 3 parameterization modes: cell+misset, U-matrix, incremental UB.

    Args:
        param_values: Dict with trainable tensors (log_scale, log_cell_*_delta, angle_*_raw,
                     orientation_vec, q_params, delta_log_*, delta_alpha/beta/gamma, q_delta)
        telemetry_state: Dict with mutable telemetry accumulators (loss traces, perf counters,
                        variance floor stats, lifecycle logs)
        stage_a_context: Dict with ROI/panel sampling state, warm cache context
        crystal: dxtbx Crystal object
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        inputs: RefinementInputs (target, loss_mask, panel_slices, trusted_mask)
        hkl_grid: Structure factor grid tensor
        hkl_metadata: HKL metadata dict
        config: RefinementConfig (use_u_matrix_parameterization, use_incremental_ub, telemetry_output_dir)
        sigma_floor_sq_cache: Optional precomputed variance floor tensor
        device: torch device
        dtype: torch dtype
        baseline_crystal: Optional baseline dxtbx Crystal for incremental UB mode

    Returns:
        Tuple of (compute_loss, closure) callables with captured lexical scope
    """
```

**Critical Implementation Notes:**

1. **Unpack ALL nonlocal variables at function start:**
   ```python
   # Unpack param_values
   log_scale = param_values['log_scale']
   log_cell_a_delta = param_values.get('log_cell_a_delta')
   log_cell_b_delta = param_values.get('log_cell_b_delta')
   log_cell_c_delta = param_values.get('log_cell_c_delta')
   angle_alpha_raw = param_values.get('angle_alpha_raw')
   angle_beta_raw = param_values.get('angle_beta_raw')
   angle_gamma_raw = param_values.get('angle_gamma_raw')
   orientation_vec = param_values.get('orientation_vec')
   q_params = param_values.get('q_params')
   delta_log_a = param_values.get('delta_log_a')
   delta_log_b = param_values.get('delta_log_b')
   delta_log_c = param_values.get('delta_log_c')
   delta_alpha = param_values.get('delta_alpha')
   delta_beta = param_values.get('delta_beta')
   delta_gamma = param_values.get('delta_gamma')
   q_delta = param_values.get('q_delta')
   params = param_values.get('params', [])  # List of Parameter objects

   # Unpack telemetry_state (mutable lists/dicts for closure capture)
   iteration_count = telemetry_state['iteration_count']
   loss_trace_sample = telemetry_state['loss_trace_sample']
   loss_trace_full = telemetry_state['loss_trace_full']
   best_loss_full = telemetry_state['best_loss_full']
   best_params_snapshot = telemetry_state['best_params_snapshot']
   chi_squared_trace_sample = telemetry_state['chi_squared_trace_sample']
   chi_squared_trace_full = telemetry_state['chi_squared_trace_full']
   chi_squared_best = telemetry_state['chi_squared_best']
   masked_mse_trace_sample = telemetry_state['masked_mse_trace_sample']
   masked_mse_trace_full = telemetry_state['masked_mse_trace_full']
   masked_mse_best = telemetry_state['masked_mse_best']
   perf_closure_evals = telemetry_state['perf_closure_evals']
   perf_validation_runs = telemetry_state['perf_validation_runs']
   perf_forward_times_ms = telemetry_state['perf_forward_times_ms']
   variance_floor_clamped_pixels = telemetry_state['variance_floor_clamped_pixels']
   variance_floor_masked_pixels = telemetry_state['variance_floor_masked_pixels']
   sigma_floor_sq_tensor = telemetry_state['sigma_floor_sq_tensor']
   telemetry_step_counter = telemetry_state['telemetry_step_counter']
   u_matrix_lifecycle_log = telemetry_state.get('u_matrix_lifecycle_log', [])
   a_star_lifecycle_log = telemetry_state.get('a_star_lifecycle_log', [])

   # Unpack stage_a_context
   stage_a_ctx = stage_a_context.get('stage_a_ctx')
   sampled_panel_ids = stage_a_context.get('sampled_panel_ids')
   use_stage_a_roi_mode = stage_a_context['use_stage_a_roi_mode']
   sampled_stage_a_indices = stage_a_context['sampled_stage_a_indices']
   full_stage_a_indices = stage_a_context['full_stage_a_indices']

   # Additional context for incremental UB mode
   U_baseline = stage_a_context.get('U_baseline')
   cell_baseline = stage_a_context.get('cell_baseline')
   ```

2. **Copy lines 1320-1903 EXACTLY including:**
   - Line 1320-1326: `telemetry_step_counter`, `u_matrix_lifecycle_log`, `a_star_lifecycle_log` initialization
   - Line 1328-1736: `def compute_loss(...)` nested function
   - Line 1738-1903: `def closure()` nested function

3. **Preserve lazy imports INSIDE nested functions:**
   - `from dbex.nanobrag_bridge import ...` stays INSIDE the `if config.use_incremental_ub:` branch (lines ~1368-1371)
   - Do NOT move imports to module level

4. **Preserve TWO nested function definitions:**
   - `def compute_loss(work_item_ids: List[int], is_full: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:`
   - `def closure():`

5. **Return tuple at end:**
   ```python
   return compute_loss, closure
   ```

6. **DO NOT change logic:** This is a pure extraction. Copy exact source lines 1320-1903, no refactoring.

7. **DO NOT wire into main function yet:** Leave `run_nanobrag_refinement` unchanged. The helper exists but is not called.

### Step 3: Verify Compilation

```bash
python -m py_compile dbex/nanobrag_refinement.py \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/compilation_check.log 2>&1

echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/compilation_check.log
```

**If compilation fails:**
- Check for missing variable unpacking (compare against Step 2 unpacking code)
- Verify helper is defined AFTER `_build_stage_a_params`
- Check that nested functions are indented correctly
- Document error in blocker report if unresolvable

### Step 4: Document Extraction

Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/helper2_extraction_summary.md`:

```markdown
# Helper 2 Extraction Summary

**Date:** 2025-11-23T050000Z
**Loop:** i=193 (ralph)
**Initiative:** ARCH-REFINE-FLOW-001 Phase B1a-loop2

## Extracted Helper

**Function:** `_build_stage_a_lbfgs_closure`
**Location:** dbex/nanobrag_refinement.py:1008-XXXX (added after _build_stage_a_params)
**Line Range (Source):** 1320-1903 (original inline location in run_nanobrag_refinement)
**Line Count:** ~584 lines (including nested functions + variable unpacking)

## Parameters (15 total)

1. param_values: Dict[str, torch.Tensor]
2. telemetry_state: Dict[str, Any]
3. stage_a_context: Dict[str, Any]
4. crystal
5. detector
6. beam
7. inputs
8. hkl_grid: torch.Tensor
9. hkl_metadata: Dict
10. config: RefinementConfig
11. sigma_floor_sq_cache: Optional[torch.Tensor]
12. device
13. dtype
14. baseline_crystal

## Nonlocal Variables Captured (~30 total)

### From param_values:
- log_scale, log_cell_a/b/c_delta, angle_alpha/beta/gamma_raw
- orientation_vec (cell+misset mode)
- q_params (U-matrix mode)
- delta_log_a/b/c, delta_alpha/beta/gamma, q_delta (incremental UB mode)
- params (list of Parameter objects)

### From telemetry_state:
- iteration_count, loss_trace_sample/full, best_loss_full, best_params_snapshot
- chi_squared_trace_sample/full, chi_squared_best
- masked_mse_trace_sample/full, masked_mse_best
- perf_closure_evals, perf_validation_runs, perf_forward_times_ms
- variance_floor_clamped_pixels, variance_floor_masked_pixels, sigma_floor_sq_tensor
- telemetry_step_counter, u_matrix_lifecycle_log, a_star_lifecycle_log

### From stage_a_context:
- stage_a_ctx, sampled_panel_ids, use_stage_a_roi_mode
- sampled_stage_a_indices, full_stage_a_indices
- U_baseline, cell_baseline

## Nested Functions Preserved

- [x] `def compute_loss(work_item_ids, is_full=False)` (lines 1328-1736 source)
- [x] `def closure()` (lines 1738-1903 source)

## Parameterization Modes Preserved

- [x] Default: cell + misset (lines ~1351-1363 source, orientation_vec)
- [x] U-matrix: config.use_u_matrix_parameterization (lines ~1401-1493 source, q_params)
- [x] Incremental UB: config.use_incremental_ub (lines ~1366-1400 source, q_delta + delta_log/delta_angles)

## Lazy Imports Preserved

- [x] `from dbex.nanobrag_bridge import derive_orientation_from_quaternion_delta, derive_B_from_cell_deltas` INSIDE `if config.use_incremental_ub:` branch (lines ~1368-1371 source)

## Return Value

Tuple of (compute_loss, closure) callables

## Compilation Check

Status: PASSED / FAILED
Exit code: ...
Error (if any): ...

## Next Steps (Loop i=194)

Extract `_run_stage_a_lbfgs` helper (~110 lines), refactor `run_nanobrag_refinement` to call all three helpers (~925→~50 lines), run regression guard test_stage_a_expansion.
```

### Step 5: Update Implementation Checklist

Edit `plans/active/ARCH-REFINE-FLOW-001/implementation.md` line ~93:

Change:
```markdown
- [ ] B1a-loop2: **Extract `_build_stage_a_lbfgs_closure` helper ONLY** (Loop i=193):
```

To:
```markdown
- [x] B1a-loop2: **Extract `_build_stage_a_lbfgs_closure` helper ONLY** (Loop i=193): ✓ COMPLETE (2025-11-23T050000Z)
```

### Step 6: Write Turn Summary

Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/summary.md`:

```markdown
### Turn Summary
Extracted second Stage A helper function (_build_stage_a_lbfgs_closure, ~584 lines) with TWO nested functions (compute_loss + closure) per approved multi-loop strategy.
Helper not yet wired into runtime (no behavior change, no regression guard needed).
Compilation check PASSED/FAILED, lexical scope preserved for ~30 nonlocal variables, all 3 parameterization modes intact.
Next loop (i=194) will extract _run_stage_a_lbfgs (~110 lines), refactor main function (~925→~50 lines), and run regression guard test_stage_a_expansion.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/ (helper2_extraction_summary.md, compilation_check.log)
```

### Step 7: Commit and Push

```bash
git add dbex/nanobrag_refinement.py \
  plans/active/ARCH-REFINE-FLOW-001/implementation.md \
  plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/

git commit -m "ARCH-REFINE-FLOW-001 Phase B1a-loop2: Extract _build_stage_a_lbfgs_closure helper

Extracted second of three Stage A helper functions (~584 lines) from inline
LBFGS closure per approved multi-loop extraction strategy (i=191 blocker).

Helper signature includes 15 parameters (param_values dict, telemetry_state dict,
stage_a_context dict, plus 11 closure context params).
Supports 3 parameterization modes: cell+misset, U-matrix, incremental UB.
Returns tuple (compute_loss, closure) with captured lexical scope for ~30 nonlocal variables.

Helper not yet wired (no runtime changes, no regression guard needed).
Compilation check PASSED.

Next loop (i=194): Extract _run_stage_a_lbfgs, refactor main function, regression guard.

Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/

tests: not run"

git push
```

---

## How-To Map

### Extraction Location
Add `_build_stage_a_lbfgs_closure` at line ~1008 in `dbex/nanobrag_refinement.py`, AFTER the `_build_stage_a_params` function.

### Source Lines
Copy from `run_nanobrag_refinement` lines 1320-1903:
- Line 1320-1326: telemetry_step_counter, lifecycle logs init
- Line 1328-1736: `def compute_loss(...)` nested function
- Line 1738-1903: `def closure()` nested function

### Variable Unpacking
Add at start of helper function (see Do Now Step 2 for complete list of ~30 variables to unpack from param_values, telemetry_state, stage_a_context).

### Compilation Check
```bash
python -m py_compile dbex/nanobrag_refinement.py
```

---

## Pitfalls To Avoid

1. **DO NOT extract helper 3 (`_run_stage_a_lbfgs`)** — This loop is ONLY helper 2
2. **DO NOT refactor main function** — Leave `run_nanobrag_refinement` unchanged
3. **DO NOT run regression guard** — Helper is not wired yet (no behavior change)
4. **DO NOT move lazy imports to module level** — Keep `from dbex.nanobrag_bridge import ...` INSIDE nested function if branches
5. **DO NOT forget variable unpacking** — ALL ~30 nonlocal variables must be unpacked at function start
6. **DO NOT modify nested function signatures** — `compute_loss` and `closure` signatures stay exactly as they are
7. **DO NOT remove comments** — Keep TORCH-*, PHYSICS-*, PERF-* annotations
8. **DO NOT introduce new logic** — Pure extraction (copy exact source lines 1320-1903)
9. **DO NOT nest helper inside run_nanobrag_refinement** — Must be module-level function
10. **DO NOT commit if compilation fails** — Debug first, helper must be syntactically valid

---

## If Blocked

### Scenario A: Compilation fails with NameError (missing variable)
**Action:**
1. Check that ALL ~30 variables are unpacked (see Do Now Step 2 unpacking code)
2. Compare error message variable name against unpacking list
3. Add missing variable unpacking at function start
4. If still failing, document error in blocker report: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/blocker.md`
5. Commit blocker report (do NOT leave workspace dirty)

### Scenario B: Compilation fails with IndentationError
**Action:**
1. Check that nested functions `compute_loss` and `closure` are indented correctly (4 spaces inside helper)
2. Verify helper function itself is module-level (NOT nested inside run_nanobrag_refinement)
3. Check that return statement is at correct indentation (same level as nested function defs)
4. If still failing, document in blocker report

### Scenario C: Unsure which variables to unpack
**Action:**
1. Read helper 1 return structure from `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/helper1_extraction_summary.md`
2. Grep for variable references inside compute_loss/closure: `grep -n "log_scale\|iteration_count\|chi_squared" dbex/nanobrag_refinement.py`
3. Use Do Now Step 2 unpacking code as authoritative list
4. If still unclear, document in blocker report with specific ambiguity

---

## Findings Applied

- **CONVERGENCE-001** (Phase B4 lifecycle telemetry): Preserve u_matrix_lifecycle_log and a_star_lifecycle_log capture in closure
- **PHYSICS-LOSS-001** (dual metric tracking): Preserve chi_squared vs masked_mse telemetry fields
- **PERF-WARM-SIM-001** (cache mode telemetry): Preserve perf_closure_evals, perf_validation_runs, perf_forward_times_ms
- **GRADIENT-001** (MOSFLM injection): Preserve crystal_overrides logic in incremental UB and U-matrix branches
- **GEOMETRY-004** (incremental UB parameterization): Preserve derive_orientation_from_quaternion_delta and derive_B_from_cell_deltas imports/calls

---

## Pointers

### Helper 1 Summary
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/helper1_extraction_summary.md` — Helper 1 return structure

### Implementation Plan
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md:93-101` — Phase B1a-loop2 checklist

### Code Target
- `dbex/nanobrag_refinement.py:1320-1903` — Source lines for helper 2 extraction

### Spec References
- `docs/spec-db-core.md:57-68` — Variance-weighted loss model (implemented in compute_loss)
- `docs/spec-db-workflow.md:40-43` — Stage A parameterization modes

---

## Next Up

**Loop i=194 (after this loop completes):**
- Extract `_run_stage_a_lbfgs` helper (~110 lines: optimizer.step + final validation)
- Refactor `run_nanobrag_refinement` to call all three helpers (~925 lines → ~50 lines)
- Update final Bragg generation to use dicts from helpers
- MANDATORY regression guard: test_stage_a_expansion MUST PASS
- MANDATORY telemetry comparison: chi² traces must match baseline (from B0 artifacts)
