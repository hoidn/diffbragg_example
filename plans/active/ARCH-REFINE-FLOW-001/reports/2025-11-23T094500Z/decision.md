# Phase C2.2 CPU Fallback Instrumentation — Root Cause Identified

## Diagnostic Results

### Extracted Conditions

```json
[
  {
    "location": "_build_stage_b_params",
    "config_stage_b_full_eval_on_cpu": true,
    "device_str": "cuda:0",
    "device_type": "device",
    "device_is_cuda": true,
    "use_stage_a_roi_mode": false,
    "use_stage_a_roi_mode_type": "bool",
    "stage_a_ctx_is_not_none": true,
    "use_stage_b_cpu_fallback": true
  },
  {
    "location": "_build_stage_b_lbfgs_closure",
    "use_stage_b_cpu_fallback": true,
    "device_param": "cuda:0",
    "eval_device": "cpu",
    "eval_device_type": "cpu"
  }
]
```

### Failing Condition

**NONE - All conditions are TRUE!**

All three CPU fallback conditions evaluate correctly:
1. `config_stage_b_full_eval_on_cpu` = **true** ✓
2. `device_is_cuda` = **true** ✓ 
3. `use_stage_a_roi_mode` = **false** (panel mode) ✓
4. `stage_a_ctx_is_not_none` = **true** ✓

**Final computed values:**
- `use_stage_b_cpu_fallback` = **true** ✓
- `eval_device` = **"cpu"** ✓

### Root Cause (HIGH confidence ~95%)

**The CPU fallback condition evaluation is CORRECT. The bug is NOT in the condition logic.**

**The actual root cause:** `_build_final_bragg_from_stage_b_telemetry` (lines 2740-2945) does NOT respect the `use_stage_b_cpu_fallback` flag. This function is called to generate the final Bragg tensor after Stage B refinement completes, and it is hardcoded to use `device` (cuda:0) in two places:

1. **Line 2902-2906 (warm cache path):** Creates `Crystal` model with `device=device` (should be `cpu` when fallback active)
2. **Line 2934-2939 (cold path):** Creates `Detector`, `Crystal`, and `Simulator` with `device=device` (should be `cpu` when fallback active)

The LBFGS closure correctly uses CPU via `eval_device` during optimization, but the final Bragg generation ignores this and tries to allocate full-detector tensors on CUDA → OOM.

**Stacktrace evidence:**
```
dbex/nanobrag_refinement.py:3126: in run_nanobrag_refinement
    bragg_full = _build_final_bragg_from_stage_b_telemetry(
dbex/nanobrag_refinement.py:2912: in _build_final_bragg_from_stage_b_telemetry
    bragg_panel = simulator.run()
../../nanoBragg/src/nanobrag_torch/simulator.py:1038: in run
    physics_intensity_flat, physics_intensity_pre_polar_flat = self._compute_physics_for_position(
...
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 856.00 MiB. GPU 0 has a total capacity of 23.56 GiB of which 51.62 MiB is free.
```

## Decision Path

**Path F (new path): CPU fallback conditions correct, but final Bragg generation ignores device routing**

The condition evaluation logic (lines 2178-2182) is PERFECT. The bug is in the final Bragg generation function which was never updated to support CPU fallback.

## Next Actions

**Targeted Fix Required:**

1. **Pass `use_stage_b_cpu_fallback` parameter to `_build_final_bragg_from_stage_b_telemetry`**
   - Add parameter to function signature (line 2740)
   - Compute `final_device = torch.device("cpu") if use_stage_b_cpu_fallback else device` at top of function
   - Replace all hardcoded `device=device` with `device=final_device`:
     - Line 2902: `Crystal(..., device=final_device, ...)`
     - Line 2906: `.to(device=final_device, ...)`
     - Line 2926: `.to(..., device=final_device)`
     - Line 2934: `Detector(..., device=final_device, ...)`
     - Line 2935: `Crystal(..., device=final_device, ...)`
     - Line 2937: `.to(device=final_device, ...)`
     - Line 2939: `Simulator(..., device=final_device, ...)`

2. **Update call site (line 3126)**
   - Add `use_stage_b_cpu_fallback=use_stage_b_cpu_fallback` to function call

3. **Verify fix:**
   - Rerun Stage B full detector test (must PASS with telemetry showing `cache_mode="warm"`, `eval_device="cpu"`)
   - Rerun Stage B small detector test (regression guard, must still PASS)

4. **Remove instrumentation:**
   - Delete diagnostic print statements from lines 2184-2197 and 2385-2394
   - Keep the CPU fallback logic itself (lines 2178-2182 and 2367-2368)

## Code Changes (Loop i=214)

Added diagnostic instrumentation to two locations:
1. `_build_stage_b_params` (after line 2182)
2. `_build_stage_b_lbfgs_closure` (after line 2368)

Instrumentation is TEMPORARY and will be removed after fix is validated.

## Blocker Status

**DIAGNOSTIC COMPLETE → Ready for targeted fix**

Root cause identified with HIGH confidence. Next loop should implement 7-line fix (1 parameter addition + 1 device computation + 5 device replacements).

