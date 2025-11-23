### Turn Summary
Identified root cause of 9.3% chi² offset: StageB.run() line 163 uses perturbed crystal params instead of baseline as base for delta reconstruction.
Planned targeted one-line fix (replace `crystal.get_unit_cell().parameters()` with `baseline_crystal.get_unit_cell().parameters()`) with regression guard validation.
Next: Ralph implements fix, runs test_stage_b_shell_modifiers, and verifies chi² offset drops to ≤0.1%.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/ (planning_summary.md, input.md)

## Loop i=210 Planning Summary

**Problem:** Engine delegation path has 9.3% chi-squared offset between Stage A final (7.053e+08) and Stage B initial (7.709e+08). Tolerance: 0.1%.

**Root Cause (HIGH confidence ~85%):**
- Location: `dbex/refinement/stage_b.py:163`
- Current code: `cell_params = crystal.get_unit_cell().parameters()`
- Bug: Uses **current/potentially-perturbed** crystal params, but Stage A telemetry deltas (lines 145-150) are relative to **BASELINE** crystal

**Analysis:**
1. Loop i=208 fix targeted wrong code path (`_build_final_bragg_from_stage_b_telemetry` used AFTER Stage B optimization for final Bragg regeneration, NOT for initial chi² computation)
2. Initial chi² computed by `_run_stage_b_lbfgs` calling `compute_loss_stage_b` at iteration 0 (line 2635)
3. Closure correctly handles baseline_misset (lines 2414-2416, 2496-2498)
4. StageB.run() correctly extracts deltas from telemetry (lines 144-151)
5. Only cell parameter base is wrong

**Fix:**
```python
# Line 163 replacement:
if baseline_crystal is None:
    raise ValueError(
        "Stage B requires baseline_crystal to reconstruct cell parameters. "
        "The cell deltas in Stage A telemetry are relative to the baseline crystal."
    )
cell_params = baseline_crystal.get_unit_cell().parameters()
```

**Validation:**
- Compilation check
- Regression guard: `test_stage_b_shell_modifiers` (small detector)
- Chi² offset verification: Stage A final ≈ Stage B initial (tolerance ≤0.1%)

**Next Loop Actions (Ralph):**
1. Apply fix at line 163
2. Run regression guard
3. Verify chi² offset ≤0.1%
4. Update implementation.md Phase C2 status
5. Commit

**Expected Outcome:**
- Test PASSES
- Chi² offset drops to ≤0.1%
- Phase C2 marked COMPLETE
- Galph plans Phase C3 (StageB wrapper) next loop
