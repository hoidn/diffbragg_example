# CPU Fallback Instrumentation Summary

## Objective

Identify which CPU fallback condition is failing, causing Stage B full detector to attempt GPU execution and OOM.

## Instrumentation Locations

### 1. `_build_stage_b_params` (dbex/nanobrag_refinement.py:2184-2197)

**Inserted after line 2182** (after `use_stage_b_cpu_fallback` is computed)

Captures all three sub-conditions and the final fallback flag:
- `config.stage_b_full_eval_on_cpu` (should be `true` for canonical runs)
- `str(device).startswith("cuda")` (device type check)
- `not use_stage_a_roi_mode` (ROI mode must be disabled for panel-mode fallback)
- `stage_a_ctx is not None` (context availability)
- `use_stage_b_cpu_fallback` (final computed boolean)

**Output format:** `CPU_FALLBACK_DIAGNOSTICS_PARAMS: {json}`

### 2. `_build_stage_b_lbfgs_closure` (dbex/nanobrag_refinement.py:2385-2394)

**Inserted after line 2368** (after `eval_device` is computed)

Captures device routing decision:
- `use_stage_b_cpu_fallback` (flag from params)
- `device` (original CUDA device parameter)
- `eval_device` (routed device: CPU if fallback active, else CUDA)
- `eval_device.type` (device type string)

**Output format:** `CPU_FALLBACK_DIAGNOSTICS_CLOSURE: {json}`

## Key Findings

**UNEXPECTED RESULT:** All conditions evaluate correctly! CPU fallback IS active for full detector.

### Small Detector (ROI mode)
```json
{
  "config_stage_b_full_eval_on_cpu": true,
  "device_is_cuda": true,
  "use_stage_a_roi_mode": true,  ← ROI mode active
  "stage_a_ctx_is_not_none": true,
  "use_stage_b_cpu_fallback": false  ← Correctly disabled for ROI mode
}
```

### Full Detector (Panel mode)
```json
{
  "config_stage_b_full_eval_on_cpu": true,
  "device_is_cuda": true,
  "use_stage_a_roi_mode": false,  ← Panel mode active
  "stage_a_ctx_is_not_none": true,
  "use_stage_b_cpu_fallback": true  ← Correctly ENABLED
}
```

**Closure confirmation (full detector):**
```json
{
  "use_stage_b_cpu_fallback": true,
  "device_param": "cuda:0",
  "eval_device": "cpu",  ← Correctly routed to CPU
  "eval_device_type": "cpu"
}
```

## Root Cause (Revised)

**The condition evaluation is PERFECT.** The bug is NOT in `_build_stage_b_params` or `_build_stage_b_lbfgs_closure`.

**Actual bug:** `_build_final_bragg_from_stage_b_telemetry` (lines 2740-2945) does NOT receive or respect the `use_stage_b_cpu_fallback` flag. This function generates the final Bragg tensor after refinement and is hardcoded to use `device=cuda:0`, ignoring the CPU fallback.

**Evidence:** CUDA OOM occurs at line 2912 (`simulator.run()`) INSIDE `_build_final_bragg_from_stage_b_telemetry`, NOT inside the LBFGS closure.

## Cleanup

**Remove instrumentation after fix is validated:**
- Delete lines 2184-2197 (PARAMS diagnostic)
- Delete lines 2385-2394 (CLOSURE diagnostic)

**Keep production code:**
- Lines 2178-2182 (CPU fallback condition logic) ✓ CORRECT
- Line 2368 (eval_device routing) ✓ CORRECT

## Next Steps

1. Pass `use_stage_b_cpu_fallback` to `_build_final_bragg_from_stage_b_telemetry`
2. Compute `final_device = torch.device("cpu") if use_stage_b_cpu_fallback else device`
3. Replace all 7 hardcoded `device=device` with `device=final_device`
4. Rerun full detector test (expected PASS with CPU fallback telemetry)
5. Remove instrumentation
6. Commit fix

