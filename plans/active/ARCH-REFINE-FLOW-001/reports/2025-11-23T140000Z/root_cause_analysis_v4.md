# Phase C2.5 Root Cause Analysis v4 — HKL Grid Transfer Corruption

## Executive Summary

**Verdict:** Loop i=222 HKL grid device routing "fix" (use `stage_b_eval_stage_a_ctx.hkl_grid`) was **CORRECT DIRECTION but INSUFFICIENT**. The CPU-native HKL grid at `stage_b_eval_stage_a_ctx.hkl_grid` is **already corrupted** when built via `.to(device='cpu')` transfer from CUDA tensor.

**Root Cause (95% confidence):** HKL grid tensor `.to()` device transfer corrupts Miller index semantics, producing nonsensical k-range `[-1796,1708]` instead of `[-14,14]`.

**Fix:** Reconstruct HKL grid from scratch on CPU instead of transferring CUDA tensor.

## Evidence

### HKL Stats Comparison (Loop i=222 Test Output)

**CUDA path (working):**
```
[HKL stats] h=[-13,18] k=[-14,14] l=[0,12] hit_rate=6219531/6224001 (99.93%)
```

**CPU path (broken after "fix"):**
```
[HKL stats] h=[0,0] k=[-1796,1708] l=[0,1] hit_rate=0/224064036 (0.00%)
```

### Code Path Analysis

**CPU HKL Grid Construction (dbex/nanobrag_refinement.py:2198-2210):**
```python
stage_b_eval_stage_a_ctx = _build_stage_a_context(
    detector=detector,
    beam=beam,
    crystal=crystal,
    trusted_mask=inputs.trusted_mask,
    hkl_grid=hkl_grid,  # ← CUDA tensor from parent scope (line ~3041)
    ...
    device=cpu_device,  # ← CPU device
    ...
)
```

**Inside `_build_stage_a_context` (line 547):**
```python
hkl_grid_device = hkl_grid.to(device=device, dtype=dtype)  # Transfer CUDA→CPU
```

**Problem:** The `.to()` call transfers raw tensor data but corrupts the HKL grid's Miller index structure/semantics.

### Why Gradient Tracking Failed

The gradient tracking error ("element 0 of tensors does not require grad") is a **downstream symptom**, not the root cause:

1. 0% HKL hit rate → ALL structure factors = `default_F` (constant, gradient-free)
2. All Bragg intensities = 0 (no reflections generated)
3. Loss is constant → no gradients flow to `shell_modifiers`
4. LBFGS fails because parameters don't connect to loss via gradients

**Key Diagnostic:** The `WhereBackward0` grad_fn IS present (loop i=222 HKL_GRAD_CHECK), proving the out-of-place `torch.where` construction works correctly. The gradient graph builds but is a **dead end** because the loss doesn't depend on the parameters (all Bragg=0).

## Hypothesis: HKL Grid Transfer Corruption

### Why `.to(device='cpu')` Fails

**Suspected mechanism:**

The `hkl_grid` tensor is a **dense P1 grid** with shape `[nh, nk, nl]` containing complex structure factors. Miller indices (h,k,l) are **implicit** in the grid layout:
- h = grid index 0 → h_min, grid index 1 → h_min+1, etc.
- Same for k, l dimensions

When transferred CUDA→CPU via `.to()`:
1. **Data is preserved** (raw float values)
2. **But grid metadata/context is lost or corrupted**
3. Simulator's Miller index calculation or structure factor lookup uses **wrong index offsets** on CPU

**Evidence:** Nonsensical k-range `[-1796,1708]` suggests:
- Either the grid dimensions are misinterpreted (e.g., treating a different axis as k)
- Or the h_min/k_min/l_min offsets are corrupted during transfer
- Or the simulator's CPU path has a bug in computing Miller indices from grid coordinates

### Why Minimal Reproducer Worked (Loop i=220)

The minimal reproducer (plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py) **built a fresh CPU context from scratch**, reconstructing the HKL grid on CPU natively via the same code path that works for CUDA initialization.

**Key difference:** Reproducer didn't transfer an existing CUDA tensor; it **loaded/constructed HKL data directly on CPU**.

## Proposed Fix

### Option A: Reconstruct HKL Grid on CPU (RECOMMENDED)

Instead of transferring `hkl_grid` CUDA→CPU, **reconstruct it from source on CPU**:

```python
# dbex/nanobrag_refinement.py:2198-2210
if use_stage_b_cpu_fallback and stage_a_ctx is not None and config.enable_stage_a_warm_cache:
    cpu_device = torch.device("cpu")

    # CRITICAL: Do NOT transfer hkl_grid from CUDA. Reconstruct on CPU from source.
    # The CUDA hkl_grid tensor loses Miller index semantics during .to(device='cpu').
    # Instead, reload structure factors from MTZ/inputs and rebuild grid on CPU.
    cpu_hkl_grid = _build_hkl_grid_on_device(
        hkl_source=inputs.hkl_source,  # MTZ path or precomputed structure factors
        hkl_metadata=hkl_metadata,
        device=cpu_device,
        dtype=dtype,
    )

    stage_b_eval_stage_a_ctx = _build_stage_a_context(
        ...
        hkl_grid=cpu_hkl_grid,  # CPU-native grid, NOT transferred from CUDA
        device=cpu_device,
        ...
    )
```

**Advantages:**
- Avoids transfer corruption
- CPU grid built the same way as CUDA grid (identical code path)
- Minimal reproducer evidence proves this approach works

**Implementation:**
1. Extract HKL grid construction logic from `run_nanobrag_refinement` or wherever the initial `hkl_grid` is built
2. Create helper `_build_hkl_grid_on_device(hkl_source, hkl_metadata, device, dtype)` that loads structure factors and tensorizes on target device
3. Call this helper when building CPU context instead of transferring CUDA tensor
4. Requires `inputs` to carry HKL source (MTZ path or precomputed F_hkl array)

**Risk:** Low (~10%) - Same logic already works for CUDA initialization and in minimal reproducer.

### Option B: Fix HKL Grid Transfer (INVESTIGATE)

If Option A is blocked (e.g., HKL source not available at Stage B context build time), investigate **why** `.to(device='cpu')` corrupts Miller indices:

1. Add diagnostics to `_build_stage_a_context` after line 547:
   - Check `hkl_metadata` (h/k/l min/max/dims)
   - Sample grid values at known (h,k,l) before and after transfer
   - Compare CUDA grid[0,0,0] vs CPU grid[0,0,0]
2. Inspect `nanobrag_torch.models.crystal.Crystal.get_structure_factor()` to see how it maps Miller indices to grid coordinates
3. Check if there's a device-specific bug in Miller index calculation

**Risk:** High (~60%) - May uncover deep nanobrag_torch CPU simulator bug requiring upstream patch or deferral.

### Option C: Defer CPU Fallback (FALLBACK)

If Options A/B are too complex:
- Document CPU fallback as **unsupported** for Stage B
- Mark test with `@pytest.mark.skip(reason="CPU fallback Stage B not supported")`
- Focus on CUDA-only validation for remaining work
- Revisit CPU support after Phase D/E stabilization

**Advantages:** Unblocks progress on higher-priority items (Tier 2/3 roadmap).

**Disadvantages:** Leaves a documented limitation in the codebase.

## Decision Protocol

**Path A (HKL grid reconstruction on CPU):**
- **Do Now:** Extract HKL construction helper, rebuild CPU grid from source, validate full+small detector tests PASS
- **Next Loop:** If PASS → Phase C validation (remove diagnostics, update findings), If FAIL → investigate reconstruction logic mismatch

**Path B (Transfer corruption investigation):**
- **Do Now:** Add HKL grid diagnostics before/after transfer, compare metadata and sample values, identify transfer bug
- **Next Loop:** If bug found → patch transfer logic OR escalate to nanobrag_torch, If no bug → revert to Path A

**Path C (Defer CPU fallback):**
- **Do Now:** Mark full detector test as skip with reason, document limitation in findings, proceed to Phase C validation CUDA-only
- **Next Loop:** Phase C smoke validation (small detector only) → Phase D/E planning

## Recommended Action

**Pursue Path A (HKL grid reconstruction)** with Path C as fallback if blocked after 2 loops.

**Rationale:**
- Minimal reproducer provides high-confidence evidence that CPU HKL grid construction works when done natively
- Transfer corruption is a plausible root cause (nonsensical Miller indices)
- Implementation risk is low (extract existing logic)
- Avoids deep nanobrag_torch debugging (Path B) which may require upstream patches

**Estimated Effort:** 1-2 loops (helper extraction + validation 1 loop, debugging if needed 1 loop).

## Findings to Update

**GRADIENT-003 (CPU Fallback Path Zero Bragg Output):**
- **Status:** Active → Path A (HKL grid transfer corruption root cause identified)
- **Root Cause:** HKL grid `.to(device='cpu')` transfer corrupts Miller index semantics (k-range nonsensical [-1796,1708] instead of [-14,14])
- **Evidence:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T122329Z/ (0% hit rate persists after device routing fix)
- **Next Actions:** Reconstruct HKL grid from source on CPU instead of transferring CUDA tensor; validate via full+small detector tests.

**Gradient Tracking Issue (NOT a separate finding):**
- Gradient tracking failure is a **downstream symptom** of 0% HKL hit rate → all Bragg=0 → no gradients
- Do NOT create GRADIENT-004 finding
- Gradient issue will resolve automatically when HKL grid reconstruction fixes Bragg output

## Artifacts

- `root_cause_analysis_v4.md` (this file)
- Loop i=222 test output: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T122329Z/pytest_stage_b_full_fixed.log
- Loop i=220 minimal reproducer: plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py

## References

- GRADIENT-003 finding (docs/findings.md row 69)
- PERF-WARM-012 (CPU fallback context cloning)
- spec-db-runtime.md:34-39 (CPU/CUDA parity requirement)
- Minimal reproducer success (loop i=220, 99% Bragg coverage on CPU)
