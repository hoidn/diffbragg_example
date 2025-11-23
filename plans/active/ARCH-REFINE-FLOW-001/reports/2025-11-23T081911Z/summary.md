### Turn Summary
Fixed signature error from loop i=208 (removed erroneous `=None` defaults from 7 required parameters in `_build_final_bragg_from_stage_b_telemetry` helper).
Analyzed why loop i=208's baseline_crystal fix didn't resolve the chi² offset: the helper is used for final Bragg regeneration AFTER Stage B optimization, not for the initial chi² computation that fails the test.
Next: Create focused diagnostic script to capture parameter state at Stage A→B boundary and identify true divergence source (cell/misset/scale/device).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/ (analysis.md, summary.md)

## Loop i=209 Details

**Problem:** 9.3% chi² offset between Stage A final (7.053e+08) and Stage B initial (7.709e+08) in engine delegation path. Tolerance: 0.1%.

**Ralph's Loop i=208 Attempt:** Added `baseline_crystal` parameter to `_build_final_bragg_from_stage_b_telemetry` helper + incorrectly added `=None` defaults to 7 required parameters.

**Why i=208 Didn't Work:** The `_build_final_bragg_from_stage_b_telemetry` helper (dbex/nanobrag_refinement.py:2713-2916) is called AFTER Stage B optimization completes to regenerate the final Bragg pattern. It is NOT used for computing the initial chi² that causes test_stage_b_shell_modifiers to fail.

The initial chi² comes from `_run_stage_b_lbfgs` line 2635 calling `compute_loss_stage_b` at iteration 0.

**Code Analysis:** Both the closure (lines 2414-2416, 2496-2498) and StageB.run() (lines 163-199) correctly handle baseline_misset. The bug must be a subtle parameter reconstruction mismatch.

**Changes This Loop:**
- Reverted signature error: removed `=None` from 7 parameters (inputs, hkl_grid, hkl_metadata, config, device, dtype) in `_build_final_bragg_from_stage_b_telemetry`
- Kept `=None` ONLY for `baseline_crystal` and `stage_a_ctx` (correct optional parameters)
- Compilation check: PASSED

**Four Hypotheses for True Bug (documented in analysis.md):**
1. **H1 (Cell Parameter Reconstruction):** StageB.run() line 163-173 uses `crystal.get_unit_cell().parameters()` which may return perturbed values instead of baseline. Cell deltas are relative to BASELINE, so reconstruction should use baseline crystal params.

2. **H2 (Scale Parameter):** Verify `log_scale` matches exactly between Stage A final validation and Stage B initial.

3. **H3 (Device/Dtype):** Check if CPU fallback logic causes device mismatch between A final and B initial computations.

4. **H4 (HKL Grid):** Verify HKL grid integrity passed to Stage B matches Stage A final exactly.

**Recommended Next Loop:** Create diagnostic script to capture exact parameter state at Stage A→B boundary (cell, misset, log_scale, device, HKL grid hash) and compare chi² computations step-by-step.

**Confidence:** HIGH (~85%) that H1 (cell parameter reconstruction) is the root cause - StageB should use `baseline_crystal.get_unit_cell().parameters()` instead of `crystal.get_unit_cell().parameters()`.
