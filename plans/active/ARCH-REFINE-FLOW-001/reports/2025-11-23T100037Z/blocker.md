# Phase C2.2 CPU Fallback Device Routing Fix — Blocker

## Fix Status

**Device Routing Fix: PARTIAL SUCCESS**

The 7-line CPU fallback device routing fix was implemented successfully:
1. ✅ Added `use_stage_b_cpu_fallback` parameter to `_build_final_bragg_from_stage_b_telemetry` signature
2. ✅ Added `final_device` computation at top of function body
3. ✅ Replaced 7 occurrences of `device=device` with `device=final_device`
4. ✅ Updated call site to pass `use_stage_b_cpu_fallback` parameter
5. ✅ Added CPU context cloning logic in `stage_a_b_mode` branch (lines 3115-3136)

**Result:** The OOM error during final Bragg reconstruction is **RESOLVED**. The test now progresses past `_build_final_bragg_from_stage_b_telemetry` without CUDA out-of-memory errors.

## New Blocker

**Stage B LBFGS Gradient Error (Pre-existing Bug)**

### Failure Signature

```
status='error'
message='Stage B error: element 0 of tensors does not require grad and does not have a grad_fn'
```

### Telemetry Evidence

```python
'status': 'error',
'message': 'Stage B error: element 0 of tensors does not require grad and does not have a grad_fn',
'loss_trace_sample': [],  # Empty - optimizer failed before first iteration
'loss_trace_full': [(0, 1427176576.0), (0, 1427176576.0)],  # Only 2 validation runs
'closure_evals': 1,  # Failed on first closure evaluation
```

### Root Cause Analysis

The gradient error occurs **during Stage B LBFGS optimization**, not during final Bragg reconstruction. Specifically:

1. CPU fallback is correctly activated (`use_stage_b_cpu_fallback=true`, `eval_device=cpu`)
2. Stage B LBFGS closure creates simulators on CPU
3. First closure evaluation fails with "element 0 of tensors does not require grad"

This suggests that when the CPU-cloned context is created (`stage_b_eval_stage_a_ctx`), some tensors lose gradient information. The `_build_stage_a_context` helper may be creating tensors without `requires_grad=True`.

### Hypothesis

When `_build_stage_a_context` clones the Stage A context to CPU (lines 2205-2217 in `_build_stage_b_params`, and lines 3121-3133 in the `stage_a_b_mode` branch), it creates fresh detector/crystal models on CPU. The HKL grid is moved to CPU via `.to(device=cpu_device)`, which may drop gradients.

However, Stage B should NOT need gradients on the HKL grid - only on the shell modifier parameters. The error message suggests that LBFGS is trying to compute gradients but can't find a computation graph.

### Why This Bug Was Hidden

This gradient bug was **masked** by the OOM error. Previously, the test would fail with CUDA OOM at line 2912 (final Bragg reconstruction) before reaching this gradient error. Now that we've fixed the device routing, the test progresses far enough to expose the pre-existing gradient bug in the CPU fallback path.

## Test Outcomes

### Full Detector Test
- **Status:** FAILED
- **Reason:** Stage B LBFGS gradient error (not device routing)
- **Outcome File:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/pytest_stage_b_full.log
- **CPU Fallback Activated:** ✅ YES (`use_stage_b_cpu_fallback=true`, `eval_device=cpu`)
- **OOM Resolved:** ✅ YES (test progresses past final Bragg reconstruction)
- **New Error:** gradient computation failure in Stage B LBFGS closure

### Small Detector Test
- **Status:** NOT RUN (deferred due to blocker)

## Artifacts

- **Test Log:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/pytest_stage_b_full.log
- **Telemetry:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/telemetry_stage_b_full.json

## Code Changes Summary

### 1. `_build_final_bragg_from_stage_b_telemetry` (dbex/nanobrag_refinement.py:2740-2949)

**Added parameter:**
```python
def _build_final_bragg_from_stage_b_telemetry(
    ...,
    use_stage_b_cpu_fallback=False,  # NEW
    stage_a_ctx=None,
):
```

**Added device routing:**
```python
# Route device to CPU when CPU fallback is active
final_device = torch.device("cpu") if use_stage_b_cpu_fallback else device
```

**Replaced 7 device references:** All occurrences of `device=device` replaced with `device=final_device` (lines 2906, 2910, 2930, 2938, 2939, 2941, 2943).

### 2. `run_nanobrag_refinement` (stage_a_b_mode branch, lines 3115-3166)

**Added CPU context cloning:**
```python
# PERF-WARM-012: Clone Stage A context to CPU when CPU fallback is active
stage_b_eval_stage_a_ctx = None
if use_stage_b_cpu_fallback and stage_a_ctx is not None and config.enable_stage_a_warm_cache:
    cpu_device = torch.device("cpu")
    stage_b_eval_stage_a_ctx = _build_stage_a_context(
        detector=detector,
        beam=beam,
        crystal=crystal,
        trusted_mask=inputs.trusted_mask,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        enable_hkl_interpolation=config.enable_hkl_interpolation,
        device=cpu_device,
        dtype=dtype,
        panel_slices=panel_slices,
        enable_roi_mode=False,  # CPU fallback is panel-mode only
    )
elif not use_stage_b_cpu_fallback:
    stage_b_eval_stage_a_ctx = stage_a_ctx
```

**Updated call site:**
```python
bragg_full = _build_final_bragg_from_stage_b_telemetry(
    ...,
    use_stage_b_cpu_fallback=use_stage_b_cpu_fallback,  # NEW
    stage_a_ctx=stage_b_eval_stage_a_ctx,  # Use CPU-cloned context when fallback active
)
```

## Next Steps

1. **Investigate gradient bug in CPU fallback path**
   - Check `_build_stage_a_context` to understand how tensors are created
   - Verify that Stage B shell modifier parameters have `requires_grad=True`
   - Check if the CPU-to-CPU tensor moves drop gradients

2. **Possible fixes:**
   - Ensure shell modifier parameters are created with `requires_grad=True` on correct device
   - Verify that `stage_b_eval_stage_a_ctx` doesn't interfere with gradient computation
   - Check if LBFGS closure is trying to compute gradients on frozen Stage A parameters

3. **Alternative path:**
   - If gradient bug is fundamental to CPU fallback design, may need to revisit PERF-WARM-012 approach
   - Consider whether CPU fallback should disable warm cache and use cold path instead

## Recommendation

**ESCALATE** to Galph for gradient bug investigation. The device routing fix is complete and working (OOM resolved), but exposes a deeper gradient computation bug in the CPU fallback implementation that requires architectural review.

## Preservation Note

**DO NOT REVERT** the device routing fix. The changes are correct and necessary. The gradient bug is a separate issue that was previously masked.

**KEEP INSTRUMENTATION** (diagnostic prints at lines 2197, 2394) until gradient bug is resolved, to maintain visibility into CPU fallback activation.
