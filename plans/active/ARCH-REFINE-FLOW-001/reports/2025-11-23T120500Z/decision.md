# Phase C2.3 Minimal Reproducer Decision

## Executive Summary

**Path B: dbex Bug — Standalone CPU Simulator Works, Zero Bragg is dbex Cache/Context Bug**

The minimal reproducer **PASSED** with 90.2% nonzero Bragg pixels on CPU, confirming that nanobrag_torch CPU simulator is **NOT broken**. The zero Bragg output observed in Stage B full detector tests is caused by a **dbex warm cache CPU context setup bug**, likely in:
1. Stage A context cloning logic (dbex/nanobrag_refinement.py:2209)
2. HKL grid device transfers
3. Warm cache crystal state management

## Reproducer Results

**Verdict:** PASS
**Device:** cpu
**Panel ID:** 0
**Bragg Statistics:**
- `min`: 0.0
- `max`: 0.086
- `mean`: 0.0108
- `nonzero_fraction`: 0.902 (90.2% pixels)
- `shape`: [2527, 2463] (6.2M pixels total)

**Interpretation:** Standalone CPU simulator produces healthy Bragg intensities with correct spatial coverage. The 90.2% nonzero fraction is consistent with expected Bragg spot density.

## Root Cause Analysis

### Hypothesis Update

**Hypothesis 5 (nanobrag_torch CPU simulator bug):** **REJECTED**
- **Reason:** Minimal reproducer proves CPU simulator works correctly in isolation
- **Confidence:** VERY HIGH (95%) that nanobrag_torch is not the root cause

**NEW Hypothesis 6 (dbex warm cache CPU context bug):** **PROMOTED to 90% confidence**
- **Reason:** Same simulator + same inputs work standalone but fail in full test context
- **Evidence:** Reproducer uses identical setup path (`_build_stage_a_context` equivalent), but minimal scope
- **Suspected Locations:**
  1. **Stage A context cloning** (dbex/nanobrag_refinement.py:2206-2221): CPU fallback path might clone stale/uninitialized crystal state from CUDA context
  2. **HKL grid device transfers**: Warm cache might reference CUDA tensors when building CPU context
  3. **Crystal model reuse**: Base crystal model might not be properly re-instantiated for CPU device

## Decision Path: B (dbex Bug — Investigate Warm Cache / Context Cloning)

Per input.md decision tree, Path B applies when reproducer PASSES.

### Evidence for Path B

1. **Standalone CPU works** (90.2% nonzero) → nanobrag_torch simulator is healthy
2. **Full test CPU fails** (100% zero) → dbex context setup has device-specific bug
3. **Parameter parity confirmed** (loop i=219) → bug is NOT in parameter construction
4. **Warm cache architecture** → CPU fallback creates new context from CUDA baseline

### Suspected Bug Locations

#### 1. Stage A Context Cloning (dbex/nanobrag_refinement.py:2206-2221)

```python
# CPU fallback path creates new StageAContext
stage_a_ctx_cpu = _build_stage_a_context(
    detector=detector,
    beam=beam,
    crystal=crystal,  # ← May have stale state from CUDA path
    trusted_mask=stage_a_ctx['trusted_masks_cpu'],
    hkl_grid=stage_a_ctx['hkl_grid'],  # ← May still be on CUDA device
    hkl_metadata=stage_a_ctx['hkl_metadata'],
    enable_hkl_interpolation=config.enable_hkl_interpolation,
    device=torch.device("cpu"),
    dtype=torch.float32,
    panel_slices=inputs.panel_slices,
    enable_roi_mode=config.enable_roi_mode,
)
```

**Potential Issues:**
- `crystal` object might retain CUDA-specific state not visible in parameter snapshots
- `hkl_grid` from `stage_a_ctx` might still be on CUDA device despite transfer attempt
- `trusted_masks_cpu` key might not exist or be incorrectly sliced

#### 2. HKL Grid Device Mismatch

The warm cache stores `hkl_grid_device` at line 547 (CUDA), but CPU fallback needs a fresh CPU transfer. If the CPU path reuses `stage_a_ctx['hkl_grid']` without re-transferring, nanobrag_torch Crystal.hkl_data will point to a CUDA tensor, causing interpolation to return zeros (or crash).

#### 3. Crystal Model Reuse

Line 561 creates `base_crystal_model` on the original device. CPU fallback must create a **new** Crystal instance on CPU; reusing the CUDA model will break.

## Next Actions

### Next Loop: dbex Warm Cache CPU Context Investigation

**Scope:** Debug and fix dbex warm cache CPU context setup

**Tasks:**
1. **Compare reproducer vs full test setup:**
   - Extract Stage A context builder call from reproducer (minimal_cpu_reproducer.py:90-160)
   - Extract Stage B CPU fallback call from nanobrag_refinement.py:2206-2221
   - Diff the two setups to find divergence

2. **Add CPU fallback diagnostics:**
   - Log `stage_a_ctx.keys()` before CPU fallback
   - Log `hkl_grid.device` in CPU context builder (line 547)
   - Log `base_crystal_model.hkl_data.device` after Crystal instantiation (line 563)
   - Log `stage_a_ctx_cpu['hkl_grid'].device` after CPU context build

3. **Hypothesis-driven fixes:**
   - **H6a (HKL grid device mismatch):** Force `hkl_grid.to("cpu")` before passing to CPU context builder
   - **H6b (Crystal state reuse):** Pass fresh `crystal.copy()` to CPU context builder
   - **H6c (Trusted mask key error):** Verify `stage_a_ctx['trusted_masks_cpu']` exists; if not, use `stage_a_ctx['trusted_masks_t'].cpu()`

4. **Validation:**
   - Re-run Stage B full detector test with CPU fallback
   - Verify Bragg nonzero fraction >0.9 (consistent with reproducer)
   - Confirm parameter parity still holds (re-run i=219 diagnostics)

5. **Root Cause Documentation:**
   - Update GRADIENT-003 finding with reproducer results and dbex bug conclusion
   - Add new finding (WARM-CACHE-001) documenting CPU context cloning bug + fix

## Confidence Assessment

**Confidence:** VERY HIGH (95%) that root cause is dbex warm cache CPU context setup, NOT nanobrag_torch simulator bug.

**Rationale:**
- Reproducer isolates nanobrag_torch and proves it works on CPU
- Full test reuses dbex warm cache architecture with complex device transfers
- Parameter diagnostics (i=219) already ruled out parameter construction bugs
- Remaining variables: cache cloning, device transfers, model reuse

## Alternative Paths (Ruled Out)

**Path A (nanobrag_torch bug):** REJECTED by reproducer PASS
**Path C (reproducer implementation bug):** N/A (reproducer succeeded)
**Path D (Environment Freeze blocker):** N/A (reproducer built successfully)

## Artifacts

- `plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_reproducer.py` — Standalone CPU reproducer script
- `reproducer_result.json` (this directory) — PASS verdict with 90.2% nonzero Bragg
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/decision.md` — Hypothesis 1 DISPROVEN (parameter parity)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/crystal_config_comparison.txt` — 100% param parity evidence

## Findings Updates

**GRADIENT-003** (CPU Fallback Path Zero Bragg Output):
- **Status:** Active → Scoped to dbex warm cache bug
- **Update:** Minimal reproducer (standalone CPU StageAContext) PASSES with 90.2% nonzero Bragg. Zero output is NOT a nanobrag_torch simulator bug. Root cause is dbex warm cache CPU context cloning (suspected: HKL grid device mismatch, crystal state reuse, or trusted mask key error).
- **Next Actions:** Debug dbex/nanobrag_refinement.py:2206-2221 (CPU fallback context builder); compare against reproducer setup; add device diagnostics; fix HKL grid / crystal transfer bugs.

## Recommended Next Loop

**DO NOT APPLY FIX** (this loop is evidence-only per input.md Mode: none).

**Next Loop Tasks (ready_for_implementation):**
1. Add CPU fallback diagnostics (HKL grid device, crystal model device, trusted mask availability)
2. Compare reproducer setup vs full test CPU fallback
3. Fix identified device transfer / cache cloning bugs
4. Re-run Stage B full detector test with CPU fallback
5. Validate Bragg nonzero fraction >0.9
6. Update GRADIENT-003 and create WARM-CACHE-001 finding

---

**Turn Summary will be written separately in summary.md per input.md step 9.**
