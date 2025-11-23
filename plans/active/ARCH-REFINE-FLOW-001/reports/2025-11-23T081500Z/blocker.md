# Phase C2 Blocker — baseline_crystal Parameter Fix Did Not Resolve Chi-Squared Offset

## Problem
After implementing the baseline_crystal parameter fix per input.md instructions, the test still fails with the same 9.3% chi-squared offset:
```
Stage B initial chi-squared 7.709e+08 != Stage A final 7.053e+08 (tolerance=0.1%)
```

## Changes Applied
1. Added `baseline_crystal=None` parameter to `_build_final_bragg_from_stage_b_telemetry` signature (line 2719)
2. Updated docstring to document baseline_crystal purpose
3. Replaced `baseline_misset_deg_tensor = None` placeholder with call to `compute_baseline_misset_deg` (lines 2817-2822)
4. Passed `baseline_crystal=baseline_crystal` in engine delegation call (line 3085)

## Analysis
The fix is structurally correct:
- `compute_baseline_misset_deg(crystal, baseline_crystal=None, device, dtype)` calls `derive_robust_misset(crystal, None, device, dtype)` when `baseline_crystal` is None
- `derive_robust_misset` returns an absolute misset tensor (NOT `None`), so the helper computation should work

However, the test still fails. This suggests:
1. The bug may not be in `_build_final_bragg_from_stage_b_telemetry` at all
2. The chi-squared offset may originate earlier in the Stage B pipeline (initial chi² computation)
3. There may be a different parameter reconstruction issue

## Signature Error
I accidentally added `=None` defaults to several required parameters (`inputs`, `hkl_grid`, `hkl_metadata`, `config`, `device`, `dtype`) when only `baseline_crystal` should have a default. This needs to be reverted.

## Next Steps
1. Revert the accidental default value additions to the helper signature
2. Investigate where Stage B initial chi² is computed
3. Check if the issue is in Stage B initialization logic, not final Bragg regeneration
4. Review how parameters are passed from Stage A telemetry to Stage B initialization

## Test Output
See: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081500Z/pytest_stage_b_baseline_crystal_fix.log`

Chi-squared values:
- Stage A final: 7.053e+08
- Stage B initial: 7.709e+08
- Offset: 9.3% (exceeds 0.1% tolerance)
