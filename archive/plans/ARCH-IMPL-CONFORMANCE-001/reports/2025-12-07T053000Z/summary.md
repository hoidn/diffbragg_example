# Loop i=119 (Ralph) — Phase B.9 baseline_alignment_factor correction

## Turn Summary
Implemented Phase B.9 cold-path baseline_alignment_factor correction: changed reconstruction.py:477-523 to compute alignment from ACTUAL cold-path output (target_mean / cold_masked_mean) instead of reusing mapping's masked_mean_ratio. Both enforcement tests PASSED (warm-cache: rel_error=0.0, cold-path: rel_error=7.58e-08 < 1e-6). Next step: update implementation.md Phase B.9 status to complete and close this initiative.

Artifacts: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T053000Z/ (pytest_phase_b9_fix.log)

## Test Results

### Warm-cache test (regression check)
```
test_stage_a_vs_reconstruction_scale PASSED
  masked_mean_stage_a      = 6.302535e+01
  masked_mean_reconstruction = 6.302535e+01
  rel_error                 = 0.000000e+00
  ratio (stage_a/reconstruction) = 1.000000
```

### Cold-path test (Phase B.9 target)
```
test_stage_a_vs_reconstruction_scale_cold_path PASSED
  masked_mean_stage_a            = 6.302535e+01
  masked_mean_reconstruction_cold = 6.302534e+01
  rel_error                       = 7.579215e-08
  ratio (stage_a/reconstruction_cold) = 1.000000
```

**Success**: Cold-path rel_error dropped from 12.77% (loop i=117 post-fix) to 7.58e-08 (< 1e-6 acceptance threshold).

## Implementation Details

**File**: dbex/refinement/reconstruction.py
**Lines changed**: 477-523 (replaced elif branch fallback logic)

**Before**: Reused `masked_mean_ratio` from calibration_metadata (assumed simulator parity between mapping and reconstruction)

**After**: Compute `baseline_alignment_factor = target_mean_masked / cold_masked_mean` from ACTUAL cold-path output

**Mathematical correctness**:
- Mapping: `bragg_final = bragg_mapping * (target_mean / bragg_mean_mapping)`
- Reconstruction cold-path must match: `bragg_recon = raw_recon * sqrt(spot) * baseline_alignment_factor`
- Therefore: `baseline_alignment_factor = target_mean / mean((raw_recon * sqrt(spot))[loss_mask])`
- This differs from Phase B.7 because reconstruction simulator produces ~13% more intensity than mapping; cannot assume parity

## Debug Output (Cold-Path Test)
```
[ARCH-CONTRACT-002 Phase B.9] Cold-path baseline alignment from actual output:
  target_mean_masked: 6.302534e+01
  cold_masked_mean (raw * sqrt(spot)): 5.917750e+02
  baseline_alignment_factor: 0.106502
  source: cold_path_actual_output
```

## Static Checks
No static checks run (no linting/type checking required per input.md; touched only one file with pure implementation logic)

## Next Steps
1. Update `plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md` Phase B.9 status to "complete"
2. Commit changes with message: `[ARCH-IMPL-CONFORMANCE-001] Phase B.9 baseline_alignment_factor correction (tests: test_stage_a_vs_reconstruction_scale test_stage_a_vs_reconstruction_scale_cold_path)`
3. Mark initiative complete (all Phase A/B items done)
