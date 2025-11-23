# Phase C2.2 CPU Fallback Gradient Bug — Warm Cache Hypothesis DISPROVEN

## Status
**BLOCKED** — Cold path also fails; root cause is NOT warm cache simulator reuse

## Executive Summary

Applied the one-line fix from Galph's root cause hypothesis (disable warm cache for CPU fallback), confirmed the fix forces cold path (`use_warm_eval=False`), but the test STILL FAILS with the identical gradient error.

**Critical Finding:** Both warm AND cold code paths exhibit the same "element 0 of tensors does not require grad and does not have a grad_fn" error. The hypothesis that warm cache simulator reuse breaks gradients is INCORRECT.

## Evidence

### Fix Applied and Verified Working
```python
# Line 2451 (dbex/nanobrag_refinement.py):
use_warm_eval = stage_b_use_warm_cache and not use_stage_b_cpu_fallback
```

**Diagnostic Output Confirms Cold Path:**
```
[CACHE_MODE_DECISION] stage_b_use_warm_cache=True, use_stage_b_cpu_fallback=True, use_warm_eval=False
```

`use_warm_eval=False` forces the COLD PATH (lines 2524-2551), which creates FRESH simulators with `hkl_grid_modified` set BEFORE simulator creation:
```python
# Line 2548 (cold path):
crystal_model.hkl_data = hkl_grid_modified
simulator = Simulator(detector=detector_model, crystal=crystal_model, ...)
```

### Test Result: FAIL (Identical Error)
```
AssertionError: Stage B loss trace empty
status='error'
message='Stage B error: element 0 of tensors does not require grad and does not have a grad_fn'
closure_evals=1
```

Same error signature as loops i=215 and i=216. The gradient graph is broken REGARDLESS of whether simulators are reused (warm) or freshly created (cold).

## Diagnostic Analysis

### What We Know
1. ✅ CPU fallback condition evaluation is CORRECT (`use_stage_b_cpu_fallback=true`)
2. ✅ Device routing is CORRECT (`eval_device="cpu"`, `shell_modifier_raw_device="cpu"`)
3. ✅ Parameter initialization is CORRECT (`shell_modifier_raw.requires_grad=true`)
4. ✅ Cache mode decision is CORRECT (`use_warm_eval=false` when CPU fallback active)
5. ✅ Cold path is being taken (confirmed by diagnostic output)
6. ❌ Gradients STILL break during backward()

### Gradient Flow Trace (Cold Path)
```
shell_modifier_raw (requires_grad=True, device=cpu)
  ↓ (softplus + clamp)
shell_modifiers (requires_grad=True?, device=cpu)
  ↓ (element-wise multiply)
hkl_grid_modified (requires_grad=???, device=cpu)
  ↓ (assigned to crystal.hkl_data)
crystal_model.hkl_data (requires_grad=???, device=cpu)
  ↓ (passed to Simulator constructor)
simulator.crystal.hkl_data (requires_grad=???, device=cpu)
  ↓ (simulator.run())
bragg_panel (requires_grad=???, device=cpu)
  ↓ (loss computation)
chi_squared_loss (requires_grad=FALSE ❌, device=cpu)
  ↓ (backward() call)
ERROR: "element 0 of tensors does not require grad"
```

**Where does gradient tracking break?** Unknown. Could be:
1. **In-place operation issue** (line 2447): `hkl_grid_modified[mask] = hkl_grid_local[mask] * modifier_value`
   - `hkl_grid_modified` is created via `.clone()` from `hkl_grid_local` (which has no gradients)
   - In-place assignment might not preserve gradients from RHS
2. **nanobrag_torch Simulator issue**: `simulator.run()` might not preserve gradients
   - Possible `.detach()` or `.no_grad()` context inside `run()`
   - Possible tensor copying without gradient tracking
3. **Device transfer issue**: Tensors moved to CPU might lose gradients (unlikely, but possible)

## New Root Cause Hypotheses (Ranked)

### Hypothesis A: In-Place HKL Modification Breaks Gradients (Confidence: 70%)
**Problem:** Line 2441-2447 constructs `hkl_grid_modified` via in-place operations:
```python
hkl_grid_modified = hkl_grid_local.clone()  # No gradients (hkl_grid_local has no grad)
for shell_idx in range(n_shells):
    mask = (shell_indices_local == shell_idx)
    modifier_value = shell_modifiers[shell_idx]  # HAS gradients
    hkl_grid_modified[mask] = hkl_grid_local[mask] * modifier_value  # In-place, breaks grad?
```

**Why it breaks:** PyTorch in-place operations on tensors without `requires_grad=True` don't automatically enable gradient tracking, even if the RHS has gradients.

**Test:** Rebuild `hkl_grid_modified` using out-of-place operations that preserve gradient graph:
```python
# Create gradient-enabled HKL grid from scratch
hkl_grid_modified = hkl_grid_local.clone()
for shell_idx in range(n_shells):
    mask = (shell_indices_local == shell_idx)
    modifier_value = shell_modifiers[shell_idx]
    hkl_grid_modified = torch.where(
        mask.unsqueeze(-1),  # Broadcast mask
        hkl_grid_local * modifier_value,  # Gradient-enabled operation
        hkl_grid_modified  # Keep existing values
    )
```

**Expected outcome if correct:** Gradients flow through to `chi_squared_loss`, backward() succeeds.

### Hypothesis B: nanobrag_torch Simulator Drops Gradients (Confidence: 25%)
**Problem:** `simulator.run()` might internally use `.detach()`, `.no_grad()`, or non-differentiable operations.

**Evidence:**
- Small detector test (CUDA, warm cache) was passing in earlier loops (needs verification)
- If small detector works but full detector (CPU fallback, cold path) fails, suggests device-specific issue OR CPU path-specific bug

**Test:** Add diagnostic BEFORE and AFTER `simulator.run()`:
```python
print(f"[BEFORE RUN] crystal.hkl_data.requires_grad={simulator.crystal.hkl_data.requires_grad}")
bragg_panel = simulator.run()
print(f"[AFTER RUN] bragg_panel.requires_grad={bragg_panel.requires_grad}, grad_fn={bragg_panel.grad_fn}")
```

**Expected diagnostic if correct:** `bragg_panel.requires_grad=False` or `grad_fn=None`

### Hypothesis C: Device Transfer Breaks Gradients (Confidence: 5%)
**Problem:** Moving tensors to CPU via `.to(device=cpu)` might break gradient tracking in specific PyTorch configurations.

**Evidence against:** PyTorch `.to()` should preserve gradients; this is a well-tested operation.

**Test:** Verify `shell_modifiers.requires_grad` is still True AFTER potential device transfers.

## Immediate Next Actions

1. **REVERT the one-line fix** (line 2451) — it doesn't solve the problem and adds complexity
2. **DO NOT remove diagnostic instrumentation** (lines 2185-2201, 2389-2405, 2453) — we need more data
3. **Test Hypothesis A** (in-place operation issue) — highest probability root cause
4. **Update docs/fix_plan.md** with this blocker and new hypotheses
5. **Mark Phase C2.2 as BLOCKED** pending Hypothesis A validation

## Files Referenced
- `dbex/nanobrag_refinement.py:2441-2447` (HKL grid modification)
- `dbex/nanobrag_refinement.py:2451` (cache mode decision — to be reverted)
- `dbex/nanobrag_refinement.py:2524-2551` (cold path simulator creation)
- `dbex/nanobrag_refinement.py:2596` (backward() call site)

## Artifacts
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/pytest_stage_b_full_diagnostic.log` (cold path failure with diagnostics)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/pytest_stage_b_full_fixed.log` (initial cold path test)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/root_cause_hypothesis.md` (Galph's warm cache hypothesis — DISPROVEN)

## Confidence Assessment
**Warm Cache Hypothesis Confidence:** 0% (DISPROVEN by diagnostic evidence)
**Hypothesis A (In-Place Operation) Confidence:** 70% (most likely, testable)
**Hypothesis B (nanobrag_torch) Confidence:** 25% (possible, requires nanobrag_torch inspection)
**Hypothesis C (Device Transfer) Confidence:** 5% (unlikely)

## Decision
**Path B from input.md decision tree:** Full FAIL, Small PASS (assumed — needs verification).
Verdict: Warm cache hypothesis INCOMPLETE; cold path also broken.
Action: Write blocker, escalate to Galph with Hypothesis A test plan.
