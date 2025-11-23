# Phase C2.2 CPU Fallback Gradient Bug — Root Cause Hypothesis v2

## Status
**HYPOTHESIS (HIGH confidence ~85%)** — Warm cache simulator reuse breaks gradient flow

## Executive Summary

Ralph's excellent diagnostic work (loop i=216) proved that:
1. ✅ Parameters ARE on CPU (device fix working)
2. ✅ `shell_modifiers` HAS `requires_grad=true` and `grad_fn`
3. ❌ `chi_squared_loss.backward()` still fails

**New Root Cause Hypothesis:** The WARM CACHE PATH reuses Stage A simulators and updates their crystal's `hkl_data` attribute after creation. nanobrag_torch's Simulator may have cached or copied the HKL data internally when first created, so updating `crystal.hkl_data` later does NOT propagate the gradient-enabled tensor through the simulator's internal computation graph.

## Evidence Chain

### 1. Warm Cache is Active
From telemetry: `cache_mode='warm'` confirms `use_warm_eval=True` (line 2450).

### 2. Warm Path Updates HKL Data on Existing Simulators
```python
# Line 2451-2471: WARM PATH
if use_warm_eval:
    warm_crystal_model = Crystal(...)
    warm_crystal_model.hkl_data = hkl_grid_modified  # ← Modified HKL data
    _retarget_stage_a_simulators(stage_b_eval_stage_a_ctx, warm_crystal_model)

# Line 2520-2521: Reuses Stage A simulators
simulator = stage_b_eval_stage_a_ctx.simulators[pid]
bragg_panel = simulator.run()  # ← Simulator may not see gradient-enabled hkl_data
```

The simulators were created in Stage A with the ORIGINAL `hkl_grid` (unmodified, no gradients). Now we're updating the crystal's `hkl_data` to `hkl_grid_modified` (gradient-enabled), but the simulator might have cached the original data.

### 3. Cold Path Creates Fresh Simulators
```python
# Line 2522-2550: COLD PATH (when use_warm_eval=False)
crystal_model.hkl_data = hkl_grid_modified  # ← Set BEFORE simulator creation
simulator = Simulator(detector=detector_model, crystal=crystal_model, ...)
bragg_panel = simulator.run()  # ← Simulator created with gradient-enabled hkl_data
```

The cold path creates NEW simulators with `hkl_grid_modified` from the start, so gradients flow through.

### 4. Why This Matters for CPU Fallback
- **CUDA path (no fallback):** Simulators on CUDA, HKL data on CUDA → warm cache likely works (gradients may flow, or bug masked by different code path)
- **CPU fallback path:** Simulators created on CUDA (Stage A), then crystal updated with CPU HKL data → warm cache + device mismatch → gradient break exposed

## The Fix

**Change line 2450** to disable warm cache when CPU fallback is active:

```python
# BEFORE (BROKEN for CPU fallback):
use_warm_eval = stage_b_use_warm_cache

# AFTER (FIX):
use_warm_eval = stage_b_use_warm_cache and not use_stage_b_cpu_fallback
```

**Rationale:**
1. Forces COLD PATH (creates fresh simulators) when CPU fallback active
2. Fresh simulators get `hkl_grid_modified` from creation → gradient flow preserved
3. Small detector (CUDA, no fallback) still uses warm cache → no performance regression
4. Full detector (CPU fallback) uses cold path → slower but CORRECT

## Validation Strategy

After applying fix:
1. **Small detector test:** PASS (CUDA, warm cache, regression guard)
2. **Full detector test:** PASS (CPU fallback, cold path, gradient bug fixed)
3. **Telemetry checks:**
   - `status='ok'` (not 'error')
   - `cache_mode='cold'` (for full detector with CPU fallback)
   - `closure_evals > 1` (optimizer ran)
   - `loss_trace_sample` not empty
   - Shell modifiers show >0.2% delta

## Confidence Assessment

**ROOT CAUSE CONFIDENCE:** 85%
- Explains why device fix alone didn't work
- Explains why `shell_modifiers.requires_grad=true` but backward() fails
- Consistent with warm cache architecture (reusing simulators)
- nanobrag_torch may cache HKL data internally (black box, can't verify directly)

**FIX CONFIDENCE:** 80%
- Simple one-line change
- Forces proven-working cold path for CPU fallback
- Preserves warm cache for non-fallback paths (no performance regression for small detector)
- Risk: Full detector refinement will be slower (cold path), but correctness > speed

## Alternative Hypotheses (Lower Confidence)

### Alt 1: nanobrag_torch has a `.no_grad()` context somewhere (20%)
- **Evidence against:** Diagnostic shows `grad_enabled=True` was added (Ralph's blocker.md:94-96)
- **Why unlikely:** If nanobrag wrapped `run()` in `no_grad()`, small detector would also fail

### Alt 2: PyTorch `.to(device=...)` breaks gradients for HKL grid (15%)
- **Evidence against:** Ralph's fix ensured devices match, `.to()` should be skipped (line 2445-2446 check)
- **Why unlikely:** Diagnostic confirms `shell_modifiers_device="cpu"` and `eval_device="cpu"` match

### Alt 3: Optimizer state corruption (5%)
- **Evidence against:** Optimizer created AFTER parameters (line 2152), devices already correct
- **Why unlikely:** If optimizer state was corrupt, ALL closures would fail, not just backward()

## Next Steps

1. Apply one-line fix to disable warm cache for CPU fallback (line 2450)
2. Run full detector test → EXPECT PASS, `cache_mode='cold'`
3. Run small detector test → EXPECT PASS, `cache_mode='warm'` (regression guard)
4. Extract metrics via T0 probe
5. If both PASS:
   - Remove instrumentation (lines 2185-2198, 2389-2405)
   - Update implementation.md Phase C2.2 COMPLETE
   - Document finding: "Warm cache simulator reuse breaks gradient flow when HKL data modified post-creation"
6. If FAIL: Escalate with deeper nanobrag_torch investigation (may need to inspect simulator internals)

## Implementation Notes

### Protected Assets
- ✅ Loop i=215 device routing fix (OOM resolved)
- ✅ Loop i=216 device-aware parameter init (correct, even if insufficient alone)
- ✅ Diagnostic instrumentation (keep until validated)

### Performance Impact
- **Small detector (CUDA, no fallback):** No change, warm cache still active ✅
- **Full detector (CPU fallback):** Switches from warm to cold → ~2-3x slower per closure eval ⚠️
  - Acceptable tradeoff: correctness > speed for canonical runs
  - Future optimization: Fix nanobrag_torch to support gradient-preserving HKL data updates

### Finding to Document (if fix succeeds)
**PERF-WARM-013**: "Warm cache simulators with post-creation HKL data updates break PyTorch autograd gradient flow. When refining shell modifiers (Stage B), disable warm cache (`use_warm_eval=False`) if the HKL grid is modified after simulator creation. This forces fresh simulator creation with gradient-enabled HKL data, preserving backward pass for LBFGS. Affects CPU fallback path; CUDA path may work due to device-specific nanobrag_torch behavior (unverified black box)."

## Time Estimate
- Implementation: 1 line change (~1 min)
- Testing: 2 test runs (~5 min total)
- Validation: Metrics extraction + decision synthesis (~2 min)
- Documentation: Instrumentation removal + findings update (~3 min)
- **Total: ~10 min** if fix succeeds

## Escalation Plan (if fix fails)
1. Add diagnostic to confirm `use_warm_eval` state in closure
2. Add diagnostic to check `simulator.crystal.hkl_data.requires_grad`
3. Manually test cold path with CPU fallback (force `use_warm_eval=False` unconditionally)
4. If cold path works → confirms hypothesis, investigate nanobrag_torch HKL caching
5. If cold path fails → different root cause, likely nanobrag_torch `.no_grad()` or `.detach()` in `run()`
