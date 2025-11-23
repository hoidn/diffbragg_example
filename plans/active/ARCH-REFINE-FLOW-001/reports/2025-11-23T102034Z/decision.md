# Phase C2.2 CPU Fallback Gradient Bugfix — Decision Synthesis

## Decision: PATH B (Full Detector FAIL)

### Test Outcomes
1. **Full Detector Test:** ❌ FAILED
   - Exit code: 1
   - Error: `Stage B error: element 0 of tensors does not require grad and does not have a grad_fn`
   - Telemetry: `closure_evals=1`, `loss_trace_sample=[]`, `status='error'`

2. **Small Detector Test:** ⏸ NOT RUN
   - Deferred due to full detector blocker

3. **Overall Verdict:** ❌ FAIL

### What Was Attempted

#### Attempt 1: Device-Aware Parameter Initialization (Per RCA)
**Change:** Created `shell_modifier_raw` on CPU when `use_stage_b_cpu_fallback=True`
```python
# Line 2127-2134: Move CPU fallback computation before parameter init
use_stage_b_cpu_fallback = (config.stage_b_full_eval_on_cpu and ...)
stage_b_param_device = torch.device("cpu") if use_stage_b_cpu_fallback else torch.device(config.device)
shell_modifier_raw = torch.zeros(..., device=stage_b_param_device, requires_grad=True)
```

**Result:** ❌ Test still failed with same error

#### Attempt 2: Enhanced Diagnostics
**Change:** Added `grad_enabled`, `is_full`, `grad_fn` diagnostics to closure
```python
# Lines 2389-2405: Enhanced diagnostic logging
eval_device_diagnostics = {
    "is_full": is_full,
    "grad_enabled": torch.is_grad_enabled(),
    "shell_modifiers_grad_fn": str(shell_modifiers.grad_fn),
    ...
}
```

**Result:** Confirmed parameters on CPU, but gradient still lost in validation calls

### Evidence Summary

#### What's Working ✓
1. **CPU Fallback Activation:** `use_stage_b_cpu_fallback=true` per config
2. **Parameter Device:** `shell_modifier_raw_device="cpu"` matches `eval_device="cpu"`
3. **Parameter Gradient Flag:** `shell_modifier_raw.requires_grad=true` throughout
4. **Device Routing Fix (Loop i=215):** OOM resolved, `_build_final_bragg_from_stage_b_telemetry` completes

#### What's Broken ❌
1. **Computed Tensor Gradient:** `shell_modifiers.requires_grad=false` on validation calls
2. **Optimizer Failure:** LBFGS `backward()` fails with "element 0 ... does not require grad"
3. **Empty Loss Trace:** `closure_evals=1`, optimizer didn't complete first iteration

### Root Cause Re-Assessment

#### Original Hypothesis (root_cause_analysis.md)
> Device mismatch (parameters on CUDA, closure on CPU) → `.to()` operation breaks gradient chain

**Status:** **PARTIALLY INCORRECT**

The fix ensures devices match (`shell_modifier_raw` on CPU, `eval_device` on CPU), so the `.to()` at lines 2442-2443 should be skipped. Yet the error persists.

#### Revised Understanding
The gradient loss likely occurs in one of these scenarios:

1. **Validation Call Confusion:**
   - Diagnostic calls showing `requires_grad=false` are the `no_grad()` validation calls (lines 2669, 2608, 2696)
   - These are EXPECTED to have no gradients (wrapped in `with torch.no_grad()`)
   - The actual optimizer closure call (inside `optimizer.step()` at line 2687) may have a DIFFERENT failure mode

2. **Autograd Graph Issue:**
   - Even if `shell_modifiers.requires_grad=true` inside the optimizer closure,the backward pass may fail if `grad_fn` doesn't properly link to `shell_modifier_raw`
   - Possible causes: detach somewhere, in-place operation, or optimizer state mismatch

3. **Optimizer State Corruption:**
   - LBFGS may have cached CUDA-device state from before the CPU fallback activation
   - Moving parameters to CPU after optimizer creation could break internal LBFGS buffers

### Confidence Assessment

**Confidence in Device Fix Correctness:** HIGH (90%)
- Parameters ARE on CPU as intended
- Diagnostics confirm device consistency
- Device routing fix from loop i=215 preserved

**Confidence in Full Bug Resolution:** LOW (30%)
- Test still fails with same error signature
- Root cause hypothesis incomplete
- May require deeper architectural investigation

### Next Actions (Escalation to Galph)

#### Recommended Path: Deeper Investigation
1. **Run enhanced diagnostic test** to distinguish validation vs optimizer calls
   - Check `is_full` and `grad_enabled` flags in next diagnostic output
   - Confirm which calls are `no_grad()` validations vs actual optimizer closures

2. **Trace autograd graph** from loss back to parameters
   - Add diagnostic in closure to print `chi_squared_loss.grad_fn` chain
   - Verify graph reaches `shell_modifier_raw` parameter

3. **Check optimizer initialization order**
   - LBFGS optimizer created at line 2142-2149 AFTER parameters
   - But `use_stage_b_cpu_fallback` computed at line 2130 (before optimizer)
   - Verify optimizer receives CPU-device parameters, not CUDA params

4. **Alternative fix candidates:**
   - Recreate optimizer after moving params to CPU?
   - Use `set_to_none=True` in `zero_grad()` calls?
   - Check if `softplus` or `clamp` operations need special handling?

#### Blocker Status
**BLOCKED** — Phase C2.2 cannot complete without resolving gradient computation bug.

**Preserve:**
- Device routing fix (loop i=215 lines 2753-2943, 3115-3143) ✓ KEEP
- CPU context cloning logic ✓ KEEP
- Diagnostic instrumentation ✓ KEEP for debugging

**Rollback:**
- None (one-line CPU param init fix is correct even if insufficient)

**Artifacts for Galph:**
- `blocker.md` — Comprehensive blocker analysis
- `pytest_stage_b_full_debug.log` — Enhanced diagnostic output
- `root_cause_analysis.md` — Original RCA (hypothesis incomplete)
- `decision.md` — This document

### Findings

None added this loop (blocker prevents validation of any hypothesis).

### Time & Effort
- **Implementation:** 2 attempts, ~30min
- **Diagnostics:** Enhanced logging added
- **Decision:** Path B escalation to Galph for architectural review

## Summary Statement
Applied device-aware parameter initialization fix per root_cause_analysis.md, but gradient error persists despite parameters correctly on CPU and devices matching. Evidence suggests original hypothesis (device mismatch → `.to()` breaks gradients) is incomplete. Likely causes: autograd graph issue, optimizer state corruption, or validation call confusion. Escalating to Galph with enhanced diagnostics for deeper architectural investigation. Loop i=215 device routing fix preserved (OOM resolved).
