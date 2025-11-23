# input.md — Loop i=194 (ARCH-REFINE-FLOW-001 Phase B1a-loop3)

## Summary
Extract `_run_stage_a_lbfgs` helper (~110 lines), refactor `run_nanobrag_refinement` to call all three extracted helpers (reducing main function ~925→~50 lines helper orchestration), and validate with regression guard.

## Mode
none (production code refactor + validation)

## Focus
ARCH-REFINE-FLOW-001 — Refactor to Protocol-based Refinement Engine (Phase B1a-loop3: final helper extraction + refactoring)

## Branch
integration

## Mapped Tests
- Regression guard: `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (MUST PASS)
- Telemetry comparison: Validate chi²/MSE traces match baseline (plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/`:
- `helper3_extraction_summary.md` — Extraction details (line ranges, parameters, return value)
- `refactoring_summary.md` — Refactoring details (before/after line counts, helper calls wiring)
- `compilation_check.log` — Python compilation check (`python -m py_compile dbex/nanobrag_refinement.py`)
- `pytest_stage_a_expansion.log` — Regression guard run (full log)
- `telemetry_comparison.json` — Chi²/MSE trace comparison metrics (initial/final values, improvement %, verdict PASS/FAIL)
- `summary.md` — Turn Summary block

---

## Do Now

**Goal:** Complete Phase B1a extraction by: (1) extracting `_run_stage_a_lbfgs` helper (~110 lines), (2) refactoring `run_nanobrag_refinement` to call all three helpers (_build_stage_a_params → _build_stage_a_lbfgs_closure → _run_stage_a_lbfgs), (3) updating final Bragg generation/telemetry packaging to use returned dicts, (4) running regression guard + telemetry comparison, (5) committing with full B1a completion message.

### Step-by-Step Protocol

#### 1. Review Phase B1a-loop2 Artifacts (5 min)

Read:
- Commit 7a06cff diff (`git show --stat 7a06cff`)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/helper2_extraction_summary.md`
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase B1a-loop2 checklist (lines 98-101)

**Context:**
- Helper 1 (`_build_stage_a_params`): lines 680-1007, ~328 lines, returns (param_values, telemetry_state, optimizer, stage_a_context)
- Helper 2 (`_build_stage_a_lbfgs_closure`): lines 1010-1726, ~717 lines, returns (compute_loss, closure)
- Both helpers extracted but NOT YET WIRED (no behavior change)

#### 2. Extract Helper 3: `_run_stage_a_lbfgs` (~110 lines)

**Source location (in current `run_nanobrag_refinement`):** Lines ~2625-2734 (between closure definition end and final Bragg generation start)

**Signature:**
```python
def _run_stage_a_lbfgs(
    compute_loss,  # Callable from helper 2
    closure,  # Callable from helper 2
    optimizer,  # torch.optim.LBFGS from helper 1
    params,  # List[Parameter] from helper 1
    telemetry_state: Dict[str, Any],  # From helper 1
    config: RefinementConfig,
    canonical_baseline: Dict[str, Any],  # From run_nanobrag_refinement
    full_stage_a_indices: List[int],  # From run_nanobrag_refinement
    log_scale,  # Parameter from helper 1
    log_cell_a_delta, log_cell_b_delta, log_cell_c_delta,  # Parameters from helper 1
    angle_alpha_raw, angle_beta_raw, angle_gamma_raw,  # Parameters from helper 1
    orientation_vec,  # Parameter from helper 1
    device,
    dtype,
) -> Tuple[str, str, Optional[float], Optional[float], Optional[Dict[str, Any]]]:
    """
    Execute Stage A LBFGS optimization and final validation.

    Returns:
        Tuple of (status, message, final_chi_squared_value, final_masked_mse_value, best_params_snapshot)
    """
```

**Extraction scope:**
- Lines ~2625-2634: `status/message` initialization, `try: optimizer.step(closure)`
- Lines ~2635-2673: Final full validation (`compute_loss(full_stage_a_indices, is_full=True)`), trace appends, best snapshot updates, canonical_baseline updates
- Lines ~2675-2683: Convergence check (improvement < min_loss_improvement → early_stop)
- Lines ~2685-2698: Exception handler, best snapshot restoration
- Lines ~2699-2734: Fallback chi²/MSE population if traces are empty

**Key mutations (helper must update these):**
- `telemetry_state['iteration_count']`, `telemetry_state['loss_trace_full']`, `telemetry_state['chi_squared_trace_full']`, `telemetry_state['masked_mse_trace_full']`, `telemetry_state['chi_squared_best']`, `telemetry_state['masked_mse_best']`, `telemetry_state['perf_validation_runs']`
- `canonical_baseline['chi_squared']`, `canonical_baseline['iteration']`
- Parameter tensors: `log_scale.data`, `log_cell_a_delta.data`, etc. (on exception path)

**Variable unpacking at helper start:**
```python
    iteration_count = telemetry_state['iteration_count']
    loss_trace_full = telemetry_state['loss_trace_full']
    chi_squared_trace_full = telemetry_state['chi_squared_trace_full']
    chi_squared_best = telemetry_state['chi_squared_best']
    masked_mse_trace_full = telemetry_state['masked_mse_trace_full']
    masked_mse_best = telemetry_state['masked_mse_best']
    best_loss_full = telemetry_state['best_loss_full']
    perf_validation_runs = telemetry_state['perf_validation_runs']
```

**Return value:**
```python
    # Update telemetry_state (mutations visible to caller via dict reference)
    telemetry_state['loss_trace_full'] = loss_trace_full
    telemetry_state['chi_squared_trace_full'] = chi_squared_trace_full
    telemetry_state['chi_squared_best'] = chi_squared_best
    telemetry_state['masked_mse_trace_full'] = masked_mse_trace_full
    telemetry_state['masked_mse_best'] = masked_mse_best
    telemetry_state['best_loss_full'] = best_loss_full

    # Canonical_baseline mutations are visible via dict reference (no need to return)

    return (status, message, final_chi_squared_value, final_masked_mse_value, best_params_snapshot)
```

**Add helper after `_build_stage_a_lbfgs_closure` (around line 1727).**

#### 3. Refactor `run_nanobrag_refinement` to Call All Three Helpers

**Current inline structure (lines ~761-2734, ~1974 lines):**
- Parameter initialization (~761-1996)
- HKL grid setup (~2000-2165)
- Telemetry/context setup (~2170-2218)
- LBFGS closure definition (~2220-2618)
- Optimizer execution + validation (~2625-2734)
- Final Bragg generation (~2736-2900)
- Telemetry packaging (~2905-3100)

**Refactored structure (~50 lines helper orchestration):**

Replace lines ~761-2734 with:

```python
    # === Stage A parameter initialization and telemetry setup ===
    # Call helper 1
    param_values, telemetry_state, optimizer, stage_a_context = _build_stage_a_params(
        crystal, detector, beam, inputs, hkl_grid, hkl_metadata, config,
        sigma_floor_sq_cache, device, dtype, baseline_detector, baseline_crystal
    )

    # Unpack needed variables for helper 2/3 calls and final Bragg generation
    log_scale = param_values['log_scale']
    log_cell_a_delta = param_values['log_cell_a_delta']
    log_cell_b_delta = param_values['log_cell_b_delta']
    log_cell_c_delta = param_values['log_cell_c_delta']
    angle_alpha_raw = param_values['angle_alpha_raw']
    angle_beta_raw = param_values['angle_beta_raw']
    angle_gamma_raw = param_values['angle_gamma_raw']
    orientation_vec = param_values['orientation_vec']
    params = param_values['params']
    baseline_misset_deg_tensor = stage_a_context.get('baseline_misset_deg_tensor')
    q_params = param_values.get('q_params')
    B_ideal_reciprocal_torch = param_values.get('B_ideal_reciprocal_torch')
    q_delta = param_values.get('q_delta')
    U_baseline = stage_a_context.get('U_baseline')
    cell_baseline = stage_a_context.get('cell_baseline')
    canonical_baseline = stage_a_context['canonical_baseline']
    full_stage_a_indices = stage_a_context['full_stage_a_indices']
    n_panels = stage_a_context['n_panels']
    panel_shape = stage_a_context['panel_shape']

    # === Stage A LBFGS closure construction ===
    # Call helper 2
    compute_loss, closure = _build_stage_a_lbfgs_closure(
        param_values, telemetry_state, stage_a_context,
        crystal, detector, beam, inputs, hkl_grid, hkl_metadata, config,
        sigma_floor_sq_cache, device, dtype, baseline_crystal
    )

    # === Stage A LBFGS execution and final validation ===
    # Call helper 3
    status, message, final_chi_squared_value, final_masked_mse_value, best_params_snapshot = _run_stage_a_lbfgs(
        compute_loss, closure, optimizer, params, telemetry_state,
        config, canonical_baseline, full_stage_a_indices,
        log_scale, log_cell_a_delta, log_cell_b_delta, log_cell_c_delta,
        angle_alpha_raw, angle_beta_raw, angle_gamma_raw, orientation_vec,
        device, dtype
    )
```

**Before/after line counts:**
- Before: `run_nanobrag_refinement` ~2400 lines (761-3100)
- After: `run_nanobrag_refinement` ~100 lines orchestration + ~2000 lines Stage B/C inline

**Critical:**
- DO NOT change any logic or computation
- DO NOT reorder operations
- PRESERVE all comments (TORCH-REFINE-*, PHYSICS-LOSS-*, etc.)
- Final Bragg generation (lines ~2736-2900) stays AS-IS (already uses direct variables, which are unpacked above)
- Telemetry packaging (lines ~2905-3100) must use telemetry_state dict for traces

#### 4. Compilation Check

```bash
python -m py_compile dbex/nanobrag_refinement.py > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/compilation_check.log 2>&1
echo $?  # MUST be 0
```

#### 5. Run Regression Guard (MANDATORY)

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/pytest_stage_a_expansion.log 2>&1
```

**Acceptance:** Test MUST PASS (1 passed, 0 failed). Any failure is a BLOCKER.

#### 6. Telemetry Comparison (Validation)

**Extract metrics from test telemetry:**
```python
import json

# Current telemetry is captured by test harness in /tmp or test artifacts
# For this validation, check the pytest log shows improvement ~18.3%
# Baseline: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/telemetry_small.json

# Quick check: grep pytest log for "improvement" line
# Full validation: If test emits telemetry JSON, compare traces

comparison = {
    "verdict": "PASS",  # or "FAIL"
    "note": "Chi² traces match, improvement ~18.3% per baseline"
}

# Save to: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/telemetry_comparison.json
```

**Verdict:** PASS if test passes AND improvement% matches baseline (~18.3%)

#### 7. Update `implementation.md` Checklist

Mark Phase B1a-loop3 as `[x]` COMPLETE (line 102 in implementation.md):

```markdown
- [x] B1a-loop3: **Extract `_run_stage_a_lbfgs` + Refactor main function** (Loop i=194): ✓ COMPLETE (2025-11-23T060000Z)
  - Extracted lines 2625-2734 (~110 lines optimizer execution + validation + convergence check)
  - Added helper at dbex/nanobrag_refinement.py:~1730 (after `_build_stage_a_lbfgs_closure`)
  - Refactored `run_nanobrag_refinement` to call all three helpers (~1974 lines → ~50 lines orchestration + ~2000 lines Stage B/C inline)
  - Regression guard PASSED (test_stage_a_expansion)
  - Telemetry comparison PASSED (chi² traces match, improvement ~18.3%)
  - Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/
```

#### 8. Write Summary and Commit

**Summary content** (`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/summary.md`):

```markdown
### Turn Summary
Completed Phase B1a extraction: all three Stage A helpers (_build_stage_a_params, _build_stage_a_lbfgs_closure, _run_stage_a_lbfgs) extracted and wired into run_nanobrag_refinement.
Main function refactored from ~1974 lines to ~50 lines helper orchestration (Stage A portion only; Stage B/C remain inline per multi-phase plan).
Regression guard PASSED (test_stage_a_expansion), telemetry comparison PASSED (chi² traces match baseline, improvement ~18.3%).
Next loop (i=195) will implement Phase B1b: wrap helpers in StageA.run() class method.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/ (helper3_extraction_summary.md, refactoring_summary.md, pytest_stage_a_expansion.log, telemetry_comparison.json)
```

**Commit message:**
```
ARCH-REFINE-FLOW-001 Phase B1a-loop3: Extract _run_stage_a_lbfgs helper, refactor run_nanobrag_refinement

Completed Phase B1a extraction by:
1. Extracting _run_stage_a_lbfgs helper (~110 lines, lines 2625-2734)
2. Refactoring run_nanobrag_refinement to call all three helpers
   (reduced Stage A portion from ~1974 lines to ~50 lines orchestration)
3. Verified regression guard PASSED (test_stage_a_expansion)
4. Verified telemetry comparison PASSED (chi² traces match, improvement ~18.3%)

All three helpers now extracted and wired:
- _build_stage_a_params (~328 lines, lines 680-1007)
- _build_stage_a_lbfgs_closure (~717 lines, lines 1010-1726)
- _run_stage_a_lbfgs (~110 lines, lines ~1730-1840)

Stage B/C remain inline (to be extracted in Phase C/D).

tests: pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion PASSED
```

#### 9. Git Operations

```bash
git add -A
git commit -m "ARCH-REFINE-FLOW-001 Phase B1a-loop3: Extract _run_stage_a_lbfgs helper, refactor run_nanobrag_refinement

Completed Phase B1a extraction by:
1. Extracting _run_stage_a_lbfgs helper (~110 lines, lines 2625-2734)
2. Refactoring run_nanobrag_refinement to call all three helpers
   (reduced Stage A portion from ~1974 lines to ~50 lines orchestration)
3. Verified regression guard PASSED (test_stage_a_expansion)
4. Verified telemetry comparison PASSED (chi² traces match, improvement ~18.3%)

All three helpers now extracted and wired:
- _build_stage_a_params (~328 lines, lines 680-1007)
- _build_stage_a_lbfgs_closure (~717 lines, lines 1010-1726)
- _run_stage_a_lbfgs (~110 lines, lines ~1730-1840)

Stage B/C remain inline (to be extracted in Phase C/D).

tests: pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion PASSED"

git push
```

---

## How-To Map

### Extraction (Helper 3)

```bash
# Identify exact line ranges
grep -n "try:" dbex/nanobrag_refinement.py | grep optimizer
grep -n "Generate final Bragg array" dbex/nanobrag_refinement.py

# Extract lines ~2625-2734 into new helper function after line 1726
# Add after _build_stage_a_lbfgs_closure
```

### Refactoring (Main Function)

```bash
# Replace lines ~761-2734 with helper calls (~50 lines)
# Keep preamble (lines 612-755) AS-IS
# Call _build_stage_a_params → unpack dicts → call _build_stage_a_lbfgs_closure → call _run_stage_a_lbfgs
# Final Bragg generation (lines ~2736-2900) stays AS-IS
# Keep Stage B/C inline AS-IS (lines ~3100+)
```

### Validation

```bash
# 1. Compilation check
python -m py_compile dbex/nanobrag_refinement.py

# 2. Regression guard
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
```

---

## Pitfalls To Avoid

1. **Variable unpacking:** Helper 3 must unpack ALL needed variables from telemetry_state dict at function start. Missing unpacking → NameError.

2. **Dict mutations:** Helper 3 mutates telemetry_state dict in place. Ensure ALL updated fields are written back to dict before return. Missing writes → telemetry loss.

3. **Parameter restoration on exception:** On exception path, helper 3 restores best_params_snapshot to parameter tensors (log_scale.data = ...). Must pass ALL parameter tensors to helper 3.

4. **Canonical_baseline mutations:** Helper 3 mutates canonical_baseline dict (chi_squared, iteration). This dict is passed by reference; no need to return it.

5. **Comment preservation:** ALL TORCH-REFINE-*, PHYSICS-LOSS-*, PERF-*, TORCH-GEOMETRY-* comments must be preserved in their original locations.

6. **Regression guard failure:** If test_stage_a_expansion FAILS after refactoring, this is a BLOCKER. Do NOT commit broken code.

7. **No new imports:** Do NOT add any new imports at file top. All imports stay in their current locations (conditional branches inside helpers).

8. **No logic changes:** Extraction and refactoring are PURE mechanical code movement. Do NOT change any computation, branching, or error handling logic.

9. **Stage B/C preservation:** Do NOT touch any code after line ~3100 (Stage B/C inline code). Phase B1a-loop3 scope is LIMITED to Stage A extraction/refactoring only.

10. **Protected Assets:** Do NOT modify HKL grid tensors, sigma_readout_t, loss_mask_t, or target_t after they are initialized.

---

## If Blocked

**Scenarios:**

### Scenario A: Regression guard FAILS after refactoring

**Actions:**
1. Compare helper calls with inline code line-by-line (diff old vs new)
2. Add debug print statements to helpers to trace parameter/telemetry flow
3. Check ALL dict writes in helper 3 are applied before return
4. If cannot resolve in 30 min, document in `blocker_regression_guard.md`
5. Commit partial progress (helper 3 extracted but not wired) with "B1a-loop3 BLOCKED" status

### Scenario B: Compilation FAIL (syntax error)

**Actions:**
1. Run `python -m py_compile dbex/nanobrag_refinement.py` to get exact line number
2. Fix syntax error (common: missing closing bracket, incorrect indentation)
3. Rerun compilation check until exit code 0
4. If syntax errors persist >3 attempts, revert to pre-extraction state
5. Document in `blocker_syntax.md`

---

## Findings Applied

- **REFINE-001:** Stage A LBFGS warm-starts scale from calibration hint. ✓ Preserved in helper 1.
- **PHYSICS-LOSS-001:** Dual metric tracking (chi²+MSE). ✓ Preserved in helpers 2/3 telemetry.
- **CONVERGENCE-001:** Zero-delta bypass for U-matrix diagnostic scripts. ✓ Not applicable to production refinement.
- **PERF-WARM-001:** Stage A warm cache via StageAContext. ✓ Preserved in helper 1 and helper 2 branching.

No relevant findings in the knowledge base require NEW code patterns for this extraction/refactoring task. All existing patterns are preserved.

---

## Pointers

### Spec/Arch References
- **docs/spec-db-workflow.md:36-45** — Stage A staging definition and zero-point invariant
- **docs/spec-db-runtime.md:18-28** — PyTorch execution guardrails

### Fix Plan References
- **docs/fix_plan.md:85-200** — ARCH-REFINE-FLOW-001 initiative, Phase B1a checklist

### Implementation Plan References
- **plans/active/ARCH-REFINE-FLOW-001/implementation.md:80-128** — Phase B1a scope, multi-loop extraction strategy

### Baseline Artifacts
- **plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/** — Phase B0 baseline telemetry + pytest logs

### Previous Loop Artifacts
- **plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/** — Phase B1a-loop1 (helper 1 extraction)
- **plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/** — Phase B1a-loop2 (helper 2 extraction)

---

## Next Up (Loop i=195, if this loop finishes early)

**Focus:** ARCH-REFINE-FLOW-001 Phase B1b — Wrap helpers in StageA.run()

**Do NOT start B1b in this loop** unless B1a-loop3 completes AND you have >30 min buffer AND telemetry comparison PASSED.

---

**END OF input.md**
