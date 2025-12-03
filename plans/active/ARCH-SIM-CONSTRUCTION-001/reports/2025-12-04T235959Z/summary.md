# ARCH-SIM-CONSTRUCTION-001 Phase C.4 Implementation Summary (Loop i=455)

## Status
**BLOCKED — suspected_spec_issue / out_of_scope_for_architecture**

## Problem
Explicit `oversample=3` parameter fix implemented as directed in input.md, but tests DB-AT-028/029 still FAIL with identical signature to Phase C.3:
- `chi²/pixel initial`: 1.084e+05 (bound: ≤1e2)
- `bragg_after_mean`: 1.0249e-05 (expected: ~0.24)
- `roi_cc_median_before`: -0.0499 (floor: ≥0.2)
- Magnitude discrepancy: **23,317×** (unchanged from prior loops)

## Implementation (Correct per Input.md)
1. **config_factories.py:48-54**: Added `oversample: int = -1` parameter to `create_detector_config()` signature
2. **config_factories.py:79-80**: Added parameter docstring explaining oversample semantics
3. **config_factories.py:230**: Forwarded `oversample=oversample` to `DetectorConfig` constructor
4. **nanobrag_bridge.py:1410**: Added `oversample=3` to `create_detector_config()` call in `simulate_forward_once` panel loop
5. **reconstruction.py:190-194**: Added `oversample=3` to `create_detector_config()` call in reconstruction cold path

All changes match input.md specification exactly. Net: 6 lines changed across 3 files.

## Evidence Analysis

### Static Inspection (Per Repeat-Failure Guard)
Examined `src/nanobrag-torch/src/nanobrag_torch/simulator.py:769-803`:
```python
if oversample is None:
    oversample = self.detector.config.oversample  # Line 770
if oversample == -1:  # Line 779
    # ... auto-selection logic ...
    print(f"auto-selected {oversample}-fold oversampling")  # Line 803
```

**Finding**: The simulator method `run()` correctly reads `self.detector.config.oversample` when `oversample` parameter is None. Since we set `DetectorConfig(oversample=3)`, the value SHOULD be 3, and auto-selection should NOT trigger.

### Observed Behavior
Test logs show **"auto-selected 3-fold oversampling"** printed repeatedly (209 times), indicating the auto-selection code path executed despite our explicit `oversample=3` setting.

**This suggests** one of:
1. `DetectorConfig.oversample` is not being set correctly (parameter rejected or ignored), OR
2. Something explicitly passes `oversample=-1` to `simulator.run()`, overriding the config, OR
3. `DetectorConfig` is reconstructed somewhere without preserving the oversample field

### Metrics Comparison
| Metric | Before Fix (Phase C.3) | After Fix (Phase C.4) | Change |
|--------|----------------------|---------------------|--------|
| Raw ratio A/B | 1.79e-07 (5,586×) | N/A (both paths log "auto-selected 3-fold") | — |
| bragg_before_mean | — | 0.239 | — |
| bragg_after_mean | — | 1.025e-05 | — |
| Magnitude ratio | — | 23,317× | **No improvement** |

The magnitude discrepancy remains essentially identical despite explicit oversample setting.

## Root Cause Hypothesis (Cannot Verify Due to Environment Freeze)
Most likely explanations:
1. **Parameter ignored**: nanobrag_torch's `DetectorConfig` dataclass might not accept/honor the `oversample` parameter
2. **Config reconstruction**: The `DetectorConfig` we create might be copied/reconstructed without the oversample field
3. **Explicit override**: Something in the call chain passes `oversample=-1` to the simulator, overriding our config

**Cannot debug further**: Per environment freeze policy (CLAUDE.md), we cannot modify nanobrag_torch source to add diagnostics or fix potential bugs.

## Repeat-Failure Guard Assessment
- ✓ **Trigger condition met**: Same acceptance criterion failed consecutively with identical signature
- ✓ **Implementation correct**: Code changes precisely match input.md specification
- ✓ **Outcome contradicts diagnosis**: input.md hypothesis (explicit oversample resolves discrepancy) did not hold
- ✓ **Attempt count**: #4 for DB-AT-028/029 under ARCH-SIM-CONSTRUCTION-001 (C.1, C.2, C.3, C.4)

Per ralph_prompt `<ground_rules/>`:
> If the same acceptance criterion failed in the prior loop with essentially the same signature and the current Do Now only adjusts gates/docs, halt immediately.

**Status**: Halted per repeat-failure guard. Marked ARCH-SIM-CONSTRUCTION-001 **blocked**.

## Initiative Type Constraints
This initiative is **architecture** type, which per `<ground_rules/>`:
> Under `architecture`, avoid changing external behavior or acceptance gates; treat any behavior drift as a bug that must be explicitly justified and paired with spec-change work.

The failure suggests:
1. **Environment issue**: nanobrag_torch (external dependency) does not support `oversample` parameter as expected → requires environment investigation (blocked by freeze policy)
2. **Spec/harness mismatch**: Test expectations may be unachievable with current nanobrag_torch → requires spec_change or harness initiative
3. **Deeper architectural issue**: Simulator construction convention mismatch extends beyond parameter passing → requires redesign

None can be resolved within an `architecture`-type initiative under repeat-failure and environment-freeze constraints.

## Recommendation
1. Mark ARCH-SIM-CONSTRUCTION-001 **blocked — suspected_spec_issue / environment_dependency**
2. Open new **diagnostics** initiative to investigate why explicit `oversample` parameter is not honored
3. Consider alternatives:
   - **Environment modification**: Upgrade/patch nanobrag_torch if version issue
   - **Architecture redesign**: If constructor pattern fundamentally incompatible
   - **Spec relaxation**: If current expectations unachievable with current tooling

## Artifacts
- `pytest_db_at_028_029.log`: Tests FAILED, 35.86s + 36.19s runs
- `dbat028/db_at_028_metrics.json`: chi²=1.084e+05, bragg_after=1.025e-05
- `metrics_comparison.json`: Before/after analysis showing no improvement
- This `summary.md`: Implementation outcome and escalation rationale

## Next Action
Escalate to supervisor (Galph) for:
- Root-cause re-analysis
- Initiative type reassessment (architecture → diagnostics or environment)
- Alternative strategy (if environment modification needed)
