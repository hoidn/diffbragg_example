# Ralph Analysis: ARCH-SIM-CONSTRUCTION-001 Phase C.1 Repeat-Failure Investigation

**Date:** 2025-12-02
**Loop:** ARCH-SIM-CONSTRUCTION-001 Phase C.1 Corrective Fix (second attempt)
**Status:** BLOCKED — Repeat-Failure Guard Triggered

## Summary

The current `input.md` requests applying `* sqrt_spot_scale` multiplication at reconstruction.py:239. However:

1. **Code already has this change** (commit acea29ef from 2025-12-02 16:31:53)
2. **Tests were NOT actually run** after that commit to verify behavior
3. **Previous Ralph analysis** (commit message) theorized "architecture tension" (double multiplication) but did not empirically test it

This violates the **repeat-failure guard**: same fix requested after it was already applied in prior loop.

## Evidence

### Current Code State (HEAD)

```python
# dbex/refinement/reconstruction.py:238
bragg_scaled = bragg_panel * scale_factor * sqrt_spot_scale
```

The multiplication IS present.

### Commit History

- **a00d42c7** (2025-12-02 16:15): Did NOT have multiplication → tests failed with `bragg_after=1.025e-05`
- **acea29ef** (2025-12-02 16:31): ADDED multiplication → tests NOT run, theoretical analysis claimed "architecture tension"

### Test Artifacts

- `2025-12-04T010500Z/pytest_db_at_028_029_fixed.log` created at 16:23 (BEFORE acea29ef commit at 16:31)
- Shows `bragg_after_mean = 1.025e-05`, `chi² = 1.084e+05` ← from code WITHOUT multiplication

### Theoretical Analysis from acea29ef

Ralph's commit message claimed:
> Evidence: bragg_panel raw=1.839e-14, scale_factor=5.572e+08 (=sqrt_spot_scale), final=5711 (vs expected 0.24). Removing sqrt gives 1.025e-05 (23,400× too small).

This suggests:
- WITH `* sqrt_spot_scale`: `bragg_after ≈ 5711` (23,400× too large)
- WITHOUT `* sqrt_spot_scale`: `bragg_after ≈ 1.025e-05` (23,400× too small)
- Missing factor: `sqrt(sqrt(spot_scale_override))` = `(spot_scale)^(1/4)` ≈ 23,400

## Root Cause Hypothesis

The theoretical analysis reveals a **fourth-root discrepancy**, not a simple double-multiplication:

```
spot_scale_override = 3.105e17
sqrt(spot_scale) = 5.572e+08  ← log_scale_baseline = log(this)
sqrt(sqrt(spot_scale)) = 23,600  ← observed missing factor
```

This suggests:

1. **log_scale_baseline architecture is correct**: `exp(log_scale_baseline) = exp(log(sqrt(spot_scale))) = sqrt(spot_scale)` ✓
2. **Simulator raw output is too small**: `bragg_panel (raw) = 1.839e-14` when it should be ~4.3e-10 (23,400× larger)
3. **Root cause is in simulator construction**, not in the reconstruction scaling logic

## Recommended Actions

Per **repeat-failure guard** (ralph_prompt §ground_rules):

> If the same acceptance criterion failed in the prior loop with essentially the same log/telemetry signature and the current Do Now only adjusts gates/docs, halt immediately.

**Required:**
1. **Run empirical test** with current code (multiplication present) to confirm actual behavior
2. **If tests still fail** with bragg_after far from 0.24:
   - DO NOT add/remove sqrt_spot_scale again
   - Escalate to Galph as suspected simulator construction issue
   - Recommend callchain analysis or diagnostics initiative to trace simulator.run() output magnitude

**Suspected Real Issue:**

The simulator raw output magnitude mismatch suggests factory contract violation or beam_config/crystal_config initialization issue. This is an **architecture** problem (matching initiative type), not a simple scaling bug.

## Next Loop Requirements

1. Complete empirical test run (currently executing)
2. Extract metrics: bragg_panel (raw), scale_factor, bragg_after_mean
3. Document findings in fix_plan.md Attempts History
4. Escalate via galph_memory.md with concrete hypothesis for supervisor investigation
