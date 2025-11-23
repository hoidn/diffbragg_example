# Phase C2.2 CPU Fallback Gradient Bug — BLOCKER

## Status
**BLOCKED** — Device routing fix applied but gradient error persists

## Summary
Applied the one-line fix from root_cause_analysis.md (create `shell_modifier_raw` on CPU when `use_stage_b_cpu_fallback=True`), but full detector test still fails with the same gradient error.

## Evidence

### Fix Applied
**File:** `dbex/nanobrag_refinement.py`
**Lines:** 2127-2144
```python
# PERF-WARM-011: Compute CPU fallback condition FIRST
use_stage_b_cpu_fallback = (
    config.stage_b_full_eval_on_cpu
    and str(device).startswith("cuda")
    and not use_stage_a_roi_mode
)

# GRADIENT-001: Create parameters on CPU when CPU fallback active
stage_b_param_device = torch.device("cpu") if use_stage_b_cpu_fallback else torch.device(config.device)
shell_modifier_raw = torch.zeros(config.stage_b_n_shells, device=stage_b_param_device, dtype=dtype, requires_grad=True)
```

### Diagnostics Confirm Fix Working
```json
CPU_FALLBACK_DIAGNOSTICS_PARAMS: {
  "use_stage_b_cpu_fallback": true,
  "stage_b_param_device": "cpu",           # ✓ CORRECT
  "shell_modifier_raw_device": "cpu",       # ✓ CORRECT
  "shell_modifier_raw_requires_grad": true  # ✓ CORRECT
}
```

### But Test Still Fails
```
FAILED tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
AssertionError: Stage B loss trace empty
status='error'
message='Stage B error: element 0 of tensors does not require grad and does not have a grad_fn'
closure_evals=1
```

### Closure Diagnostics Show Gradient Loss
```json
# First call (validation before optimizer.step):
CPU_FALLBACK_DIAGNOSTICS_CLOSURE: {
  "shell_modifier_raw_device": "cpu",
  "shell_modifier_raw_requires_grad": true,   # ✓ Parameter OK
  "shell_modifiers_device": "cpu",
  "shell_modifiers_requires_grad": false,     # ❌ GRADIENT LOST!
  "eval_device": "cpu"
}

# Second call (inside optimizer.step):
CPU_FALLBACK_DIAGNOSTICS_CLOSURE: {
  "shell_modifiers_requires_grad": true       # ✓ Gradient present
}

# Third call (validation after optimizer.step fails):
CPU_FALLBACK_DIAGNOSTICS_CLOSURE: {
  "shell_modifiers_requires_grad": false      # ❌ GRADIENT LOST
}
```

## Root Cause Re-Analysis

### Original Hypothesis (from root_cause_analysis.md)
Device mismatch between parameter creation (CUDA) and closure execution (CPU) causes `.to()` operation at lines 2442-2443 to break gradient chain.

### New Evidence
1. **Parameters ARE on CPU** — `shell_modifier_raw_device="cpu"` confirms fix working
2. **Devices match** — `shell_modifiers_device="cpu"` and `eval_device="cpu"` match
3. **`.to()` should be skipped** — Condition `if modifier_value.device != eval_device` should be false
4. **But gradient is still lost** — `shell_modifiers_requires_grad=false` on first/third calls

### Revised Hypothesis
The gradient loss occurs BEFORE the `.to()` operation, during the computation:
```python
shell_modifiers = torch.nn.functional.softplus(shell_modifier_raw) * 2.0  # Line 2383
shell_modifiers = torch.clamp(shell_modifiers, max=config.stage_b_max_modifier)  # Line 2384
```

Possible causes:
1. **no_grad() context** — First/third calls (showing `requires_grad=false`) are the validation calls wrapped in `with torch.no_grad()` at lines 2669, 2608, 2696
2. **Actual optimizer.step() failure** — Second call (showing `requires_grad=true`) is inside optimizer.step(), but backward() fails anyway
3. **Missing grad_fn** — Even though `requires_grad=true` on second call, the gradient graph may not properly link back to `shell_modifier_raw`

## Next Steps

### Option A: Enhanced Diagnostics
Add `grad_enabled`, `is_full`, and `grad_fn` info to distinguish validation calls from optimizer calls:
- Validation calls: `is_full=True`, `grad_enabled=False`
- Optimizer calls: `is_full=False`, `grad_enabled=True`

Already implemented in latest code (lines 2394-2395, 2403).

### Option B: Alternative Fix
If `.to()` isn't the issue, the problem might be:
1. Optimizer not finding parameters (check `stage_b_params` list)
2. Autograd graph broken elsewhere (trace backward from loss to params)
3. LBFGS internal issue with device-mismatched initial state

### Option C: Escalate to Galph
If enhanced diagnostics don't reveal clear root cause, this may require architectural investigation beyond a one-line fix.

## Test Command
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
```

## Artifacts
- `pytest_stage_b_full_debug.log` — Full test output with enhanced diagnostics
- `root_cause_analysis.md` — Original RCA (hypothesis may be incomplete)
- `blocker.md` — This document

## Decision
**Path B (full detector FAIL)** — Gradient bug not fully resolved by device routing fix alone. Need to:
1. Review enhanced diagnostics from next test run
2. Determine if issue is with validation calls vs optimizer calls
3. Trace gradient graph from loss back to parameters
4. Consider escalating to Galph if root cause remains unclear
