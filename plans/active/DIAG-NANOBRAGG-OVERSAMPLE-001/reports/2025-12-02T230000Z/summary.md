# Loop Summary — 2025-12-02T230000Z

## Problem
DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C.9: Apply BeamConfig flux=1.0 default fix per beam_flux_investigation.md Option A recommendation.

## Implementation
Applied 1-line fix to BeamConfig dataclass:
- File: `src/nanobrag-torch/src/nanobrag_torch/config.py:526`
- Change: `flux: float = 0.0` → `flux: float = 1.0`
- Comment updated: `# Photons per second (1.0 = neutral dimensionless scale when unknown)`
- Patch file: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/beam_flux_default_fix.patch`
- Rebuild: Successful (exit code 0), installed package confirmed to have flux=1.0 default

## Test Results
**FAILED**: Both DB-AT-028 (SKIPPED) and DB-AT-029 (FAILED) still show zero simulator output:
- bragg_panel[0] mean (raw sim output): 0.000000e+00
- bragg_full mean (final output): 0.000000e+00
- DB-AT-029: AssertionError: No valid ROI correlations computed for bragg_before

## Root Cause Analysis
**SUSPECTED IMPLEMENTATION DEFECT**: Investigation's recommendation appears incorrect.

**Evidence**:
1. Changed flux default from 0.0 to 1.0 and rebuilt nanobrag_torch successfully
2. Verified installed package has flux=1.0 default
3. Tests still fail with identical zero-output signature
4. Source code analysis reveals **flux is NOT used in simulator computation**:
   - flux only appears in config.py and __main__.py (CLI parsing)
   - Simulator code does NOT reference flux
   - flux is only used in BeamConfig.__post_init__ to recompute fluence when flux != 0 and exposure > 0 and beamsize_mm >= 0
5. When exposure=0.0 (default), fluence is NOT recomputed, so changing flux from 0 to 1 has no effect
6. beam_flux_investigation.md claims "simulator multiplies structure factors by flux" but no code path supports this

**Conclusion**: The recommended fix cannot resolve zero simulator output because flux is not used in simulator intensity computation.

## Next Actions
Per repeat-failure guard (CLAUDE.md ground_rules): **HALT** and escalate.

This is essentially loop 2 for the same acceptance criterion with the same failure signature. Before proceeding:

1. **Static inspection required**: Run prompts/callchain.md to understand actual intensity computation
2. **Re-investigate root cause**: Identify where simulator multiplies intensity and what controls scaling
3. **Consider initiative type change**: May need spec-change or architecture initiative instead of diagnostics

## Blocked Status
- **Reason**: suspected_implementation_defect — flux default change insufficient
- **Evidence Path**: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T230000Z/pytest_db_at_028_029_flux_fix.log

## Artifacts
- Patch file: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/beam_flux_default_fix.patch
- Rebuild log: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T230000Z/nanobragg_rebuild_flux_fix.log
- Test log: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T230000Z/pytest_db_at_028_029_flux_fix.log

## Metrics
- Tests run: 2 (1 skipped, 1 failed)
- bragg_before mean: 0.0 (UNCHANGED)
- bragg_after mean: 0.0 (UNCHANGED)
