# Phase C2 Bugfix Planning — Missing baseline_crystal Parameter (Loop i=208)

## Problem Statement

Ralph's Phase C2 loop i=206 (commit a82893e, 2025-11-23T075320Z) discovered a 9.3% chi-squared offset between Stage A final (7.053e+08) and Stage B initial (7.709e+08) values when using RefinementEngine delegation path (enable_stage_c=False AND enable_stage_b=True).

Ralph successfully fixed 3 AttributeErrors in loop i=206:
1. Line 3089-3090: Added `asdict()` conversion for RefinementTelemetry dataclass instances
2. Line 2853: Fixed typo `config.enable_warm_cache` → `config.enable_stage_a_warm_cache`
3. Verified StageB.name property returns `"stage_b"` (no fix needed)

However, the chi-squared offset persisted after these bugfixes, indicating a **deeper implementation defect** in the engine delegation path.

## Root Cause Analysis

The `_build_final_bragg_from_stage_b_telemetry` helper (dbex/nanobrag_refinement.py:2713-2910) is **missing the `baseline_crystal` parameter**, causing incorrect misset computation in the final Bragg array regeneration.

**Evidence:**
1. **Engine inputs include baseline_crystal** (line 3035-3036):
   ```python
   engine_inputs = {
       ...
       'crystal': crystal,
       'baseline_crystal': baseline_crystal,  # ✅ Passed to engine
       'baseline_detector': baseline_detector,
   }
   ```

2. **Helper call does NOT pass baseline_crystal** (line 3071-3084):
   ```python
   bragg_full = _build_final_bragg_from_stage_b_telemetry(
       telemetry_a=telemetry_a_raw,
       telemetry_b=telemetry_b_dict,
       detector=detector,
       beam=beam,
       crystal=crystal,            # ✅ Passed
       # ❌ baseline_crystal NOT passed
       inputs=inputs,
       ...
   )
   ```

3. **Helper always sets baseline_misset=None** (lines 2812-2814):
   ```python
   # Compute baseline misset if available
   baseline_misset_deg_tensor = None
   # Note: baseline_crystal would need to be passed to this helper to compute baseline misset
   # For now, we'll skip baseline misset support in engine path (matches inline path logic)
   ```

4. **Inline path correctly computes baseline_misset** (lines 3115-3120):
   ```python
   baseline_misset_deg_tensor = compute_baseline_misset_deg(
       crystal,
       baseline_crystal,  # ✅ Passed from function parameters
       device=device,
       dtype=dtype,
   )
   ```

5. **compute_loss_stage_b adds baseline+delta** (lines 2414-2416):
   ```python
   misset_override = misset_eval
   if baseline_misset_eval is not None:
       misset_override = baseline_misset_eval + misset_eval  # ✅ Correct math
   ```

6. **Helper does the same add BUT baseline is always None** (lines 2846-2850):
   ```python
   if baseline_misset_deg_tensor is not None:
       final_misset = baseline_misset_deg_tensor + misset_xyz_deg  # ✅ Correct logic
   else:
       final_misset = misset_xyz_deg  # ❌ WRONG: uses only delta, missing baseline
   ```

**Conclusion:** The helper uses `misset_xyz_deg` alone (just the delta from Stage A refinement), while `compute_loss_stage_b` correctly uses `baseline_misset + misset_xyz_deg`. This causes the final Bragg array to be generated with a different crystal orientation than the Stage B loss computation, resulting in the 9.3% chi-squared mismatch.

## Fix Strategy

Add `baseline_crystal` parameter to `_build_final_bragg_from_stage_b_telemetry` helper and compute `baseline_misset_deg_tensor` using the same logic as the inline path.

**Changes Required:**
1. Add `baseline_crystal=None` parameter to helper signature (line 2718)
2. Update docstring Args section to document baseline_crystal
3. Replace `baseline_misset_deg_tensor = None` placeholder with actual computation using `compute_baseline_misset_deg` (matching inline path lines 3115-3120)
4. Pass `baseline_crystal=baseline_crystal` in engine delegation call (line ~3077)

**Validation:**
- Rerun `test_stage_b_shell_modifiers` with small detector
- Verify Stage B initial chi² ≈ Stage A final chi² (relative tolerance ≤ 0.1%)

## Delegated Tasks

Ralph will execute Phase C2 bugfix implementation per `input.md` (2025-11-23T081500Z):
1. Add `baseline_crystal` parameter to helper signature + docstring
2. Replace baseline_misset placeholder with `compute_baseline_misset_deg` call
3. Pass `baseline_crystal` in engine delegation helper call
4. Rerun regression guard (test_stage_b_shell_modifiers small detector)
5. Verify chi-squared offset ≤ 0.1%
6. Commit if test passes

## Expected Outcome

After fix:
- Stage B initial chi² should match Stage A final chi² within 0.1% tolerance
- test_stage_b_shell_modifiers (small detector) should PASS
- Engine delegation path parity with inline path restored

If test still fails:
- Ralph will document blocker in `blocker.md` with exact chi² values
- Galph will review blocker and decide escalation path

## Artifacts

- **Input file**: `input.md` (Do Now with 9-step implementation plan)
- **Test selector**: `NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -k small --tb=short -v`
- **Regression guard log**: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081500Z/pytest_stage_b_baseline_crystal_fix.log`
- **Chi² comparison**: Extract from regression guard log after fix

## Related Findings

- **GEOMETRY-003**: Crystal misset computation via `compute_baseline_misset_deg` (baseline A* matrix → XYZ Euler)
- **PHYSICS-LOSS-001**: Variance-weighted chi-squared dual metrics (Stage A/B chi_squared_trace_full continuity)

## Next Actions

- Ralph executes bugfix per `input.md` Do Now
- If PASS: Mark Phase C2 complete, prepare Phase C3 planning
- If FAIL: Document blocker, escalate to Galph for root cause re-analysis
