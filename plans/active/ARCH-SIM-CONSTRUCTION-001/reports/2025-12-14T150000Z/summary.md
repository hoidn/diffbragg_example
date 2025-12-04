# ARCH-SIM-CONSTRUCTION-001 Validation Run Summary

## Loop Metadata
- Timestamp: 2025-12-14T150000Z
- Initiative: ARCH-SIM-CONSTRUCTION-001 (typed_as: bugfix, mode: parity)
- Focus: Validate StageAArtifacts wiring and warm cache reuse
- Implementation status: Code already complete (commit 3614acf4 from Phase C.9)
- Task: Re-run validation tests to capture artifact evidence

## Validation Results

### Baseline Probe (compare_stage_a_baseline.py)
**Status**: ✅ PASS (warm cache working correctly)

Key metrics:
- Telemetry model_mean_masked: 3.770721
- Reconstructed bragg mean (masked): 3.816814  
- **Ratio**: 0.987924 (98.8% - excellent parity!)
- Mask checksum match: PASS
- Warm cache indicators: `warm_cache_available=true`, `stage_a_ctx_used=true`

### DB-AT-028/029 Pytest Tests  
**Status**: ❌ FAIL (warm cache NOT working in pytest fixture)

Key metrics (DB-AT-028):
- Telemetry model_mean_masked: 11.572992
- Reconstructed bragg mean (masked, initial): 1.243596
- Reconstructed bragg mean (masked, final): 0.390298
- **Ratio (initial)**: 0.107457 (10.7% - very poor!)
- **Ratio (final)**: 0.033725 (3.4% - terrible!)
- Mask checksum match: PASS (masks are identical)
- Chi²/pixel: 2.097e5 (vs ≤1e2 spec) - FAIL
- ROI correlation: -0.054 (vs ≥0.2 floor) - FAIL

## Key Findings

1. **Probe vs Pytest Discrepancy**: The baseline probe successfully uses warm cache (0.988 ratio), but the pytest fixture does NOT (0.107 ratio for initial params). Both run the same Stage A code but produce different telemetry (different scale_factors: 1.59e10 vs 5.2e9), indicating they use different input data or random seeds.

2. **Warm Cache Implementation Exists**: Code in `tests/dbex/test_stage_a_smoke_parity.py` (lines 163-221) defensively fetches `stage_a_artifacts = getattr(engine, "_artifacts", {}).get("stage_a")` and attempts to reuse `stage_a_ctx` and cached `bragg_full`.

3. **Artifacts Not Populated in Pytest Path**: The poor reconstruction ratios (0.107 vs telemetry) suggest `stage_a_artifacts` is None or `stage_a_ctx` is None, forcing the fallback to cold reconstruction path. This matches the input.md acceptance signature: "StageAArtifacts is missing".

4. **Mask Parity Confirmed**: Phase C.10 mask provenance tracking shows `checksum_mismatch=false` in all runs, confirming masks are identical between telemetry and reconstruction. The 10-30× magnitude gaps are NOT due to mask differences.

## Artifacts Captured

- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/stage_a_baseline_probe.json` (probe showing warm cache success)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_028/baseline_stats.json` (pytest showing warm cache failure)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_029/baseline_stats.json`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/pytest_db_at_028_029.log`

## Recommended Next Steps

Per input.md expected outcome: "explicitly records that `_artifacts["stage_a"]` was missing so we can escalate the engine plumbing next loop."

1. **Debug why pytest fixture doesn't populate/reuse artifacts**: Add debug logging to `stage_a_smoke_result` fixture to confirm whether `engine._artifacts["stage_a"]` is None after `engine.run()`.

2. **Check StageA.run() return path**: Verify that StageA returns `StageResult(artifacts=StageAArtifacts(...))` in the pytest context. The probe uses a different entry point and may trigger different code paths.

3. **Escalate to supervisor**: Architecture initiative cannot change test gates. Mask parity is confirmed but intensity parity is NOT achieved. Need supervisor guidance on whether to:
   - Continue debugging artifact plumbing (engine issue)
   - Investigate why probe and pytest use different telemetry/scale_factors (test fixture issue)
   - Accept that warm cache works (probe proves it) and address underlying physics/scale issues separately

## Repeat-Failure Guard Status

Tests have failed with same signature across multiple Phase C iterations:
- Phase C.7-C.9: Chi²~2.1e5, ROI corr~-0.05
- Phase C.10 (current): Chi²=2.097e5, ROI corr=-0.054

Per repeat-failure guard: Stop after same criterion fails with same signature multiple times without material changes. Recommend supervisor analysis before next implementation loop.
