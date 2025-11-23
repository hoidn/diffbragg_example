# Phase C2 Chi² Offset Bugfix — Planning Summary (Loop i=210)

## Problem

Engine delegation path has 9.3% chi-squared offset between Stage A final (7.053e+08) and Stage B initial (7.709e+08). Tolerance: 0.1%.

## Root Cause Identified

**Location:** `dbex/refinement/stage_b.py:163`

**Current code:**
```python
cell_params = crystal.get_unit_cell().parameters()
```

**Bug:** This extracts parameters from the **current/potentially-perturbed** crystal object, but the deltas extracted from Stage A telemetry (lines 145-150) are **relative to the BASELINE** crystal.

**Impact:** Cell parameter reconstruction applies deltas (e.g., `log_cell_a_delta`) on top of already-perturbed values instead of baseline values, producing incorrect cell dimensions at Stage B initialization.

## Analysis Confidence

HIGH (~85%). The hypothesis H1 from loop i=209 analysis.md is correct:
- StageB.run() correctly extracts deltas from telemetry (lines 145-150)
- Closure correctly handles baseline_misset (lines 2414-2416, 2496-2498)
- Telemetry structure is correct (Stage A stores initial/final/delta)
- `baseline_crystal` is available (line 111)

The only remaining divergence point is the cell parameter base.

## Fix

Replace line 163:
```python
cell_params = crystal.get_unit_cell().parameters()
```

With:
```python
# Use baseline crystal params as the base for delta reconstruction
# (log_cell_*_delta are relative to BASELINE, not current crystal)
if baseline_crystal is None:
    raise ValueError(
        "Stage B requires baseline_crystal to reconstruct cell parameters. "
        "The cell deltas in Stage A telemetry are relative to the baseline crystal."
    )
cell_params = baseline_crystal.get_unit_cell().parameters()
```

## Validation Strategy

1. **Compilation check:** Verify syntax and imports
2. **Regression guard:** Run `test_stage_b_shell_modifiers` (small detector)
3. **Chi² offset check:** Verify Stage A final chi² ≈ Stage B initial chi² (tolerance ≤0.1%)
4. **Telemetry integrity:** Confirm Stage B telemetry structure unchanged

## Artifacts

- Reports root: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/`
- Planning summary: `planning_summary.md` (this file)
- Test logs: `pytest_stage_b_c2.log` (Ralph will generate)
- Summary: `summary.md` (Ralph will generate)

## Dependencies

None. This is a targeted bugfix for Phase C2.

## Next Actions After Fix

If bugfix succeeds:
- Mark Phase C2 COMPLETE
- Plan Phase C3 (StageB wrapper implementation)

If bugfix fails:
- Ralph documents blocker
- Galph reviews and decides (debug/escalate)
