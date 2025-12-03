# DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C Planning — Config Lifecycle Fix

## Loop Context
**Date**: 2025-12-03T050000Z
**Action Type**: Planning (supervisor-side analysis after repeat failure)
**Dwell**: 3 (Phase A: evidence, Phase B: implementation [failed], Phase C: planning)

## Ralph's Phase B Discovery

Ralph implemented the deep copy fix per Phase A diagnosis but discovered it was insufficient:
- **Test result**: DB-AT-028 still FAILED (chi²/pixel = 1.091e+05, unchanged from baseline 1.084e+05)
- **Debug pattern**: 2/292 configs have `oversample=3`, 290/292 have `oversample=-1`
- **First divergence**: Second simulator invocation (not first as Phase A predicted)

Ralph's excellent summary.md revealed:
> "The deep copy fix prevents mutation WITHIN each Detector instance (working as designed), but it doesn't prevent upstream code from creating NEW DetectorConfig instances with the default `oversample=-1` value."

**Phase A root cause analysis was WRONG**. The problem isn't mutation—it's creation of 290 configs with wrong default values.

## Supervisor-Side Analysis (This Loop)

Per repeat-failure escalation rule, performed code inspection before issuing another implementation Do Now.

### Callchain Trace

Traced DetectorConfig creation from test fixture → Stage A → warm simulator context:

1. **Test fixture** (`tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result`):
   - Calls `build_refinement_context` → Stage A → warm context builder

2. **Warm context builder** (`dbex/refinement/stage_a_utils.py::_build_stage_a_context`):
   - **Line 286-290**: Panel-mode simulators
     ```python
     detector_config = create_detector_config(
         panel=panel,
         beam=beam,
         trusted_mask=trusted_mask[pid]
     )  # ← Missing oversample parameter!
     ```
   - **Line 326-331**: ROI-mode simulators (same issue)

3. **Cold-path fallback** (`dbex/refinement/stage_a_utils.py::_compute_panel_loss`):
   - **Line 480-484** (diagnostic branch): Same missing parameter
   - **Line 572-576** (fast-path branch): Same missing parameter

### Root Cause (Corrected)

**Location**: `dbex/refinement/stage_a_utils.py` (4 call sites in `_build_stage_a_context`, 2 call sites in `_compute_panel_loss`)

**Problem**: `create_detector_config()` signature has `oversample: int = -1` parameter (dbex/refinement/config_factories.py:54), but none of the warm simulator call sites pass it.

**Why 2/292 have oversample=3**:
- Likely the initial/final validation configs created elsewhere (need to verify in Phase C debug logs)
- 290 configs created during warm simulator setup all use default `-1`

### Fix Strategy

**Option A** (chosen): Thread `oversample` through `RefinementConfig` + warm simulator context
- Add `oversample: int = 3` field to `RefinementConfig`
- Update `_build_stage_a_context` signature to accept `config: RefinementConfig`
- Pass `oversample=config.oversample` to all 6 `create_detector_config` call sites
- **Pros**: Clean, spec-compliant (oversample is a global simulation parameter), easy to test
- **Cons**: Requires threading `config` through call chain (~5 call sites)

**Option B** (rejected): Make `DetectorConfig` frozen/immutable
- Would catch the symptom but not fix the root cause
- Still need to pass correct `oversample` value at creation time

**Option C** (rejected): Store `oversample` in `StageAContext`
- Violates separation of concerns (context is warm cache state, not job config)
- Still requires threading through call chain

## Scope and Change Impact

### Files to modify:
1. **dbex/refinement/config.py** (+1 field)
   - Add `oversample: int = 3` to `RefinementConfig`

2. **dbex/refinement/stage_a_utils.py** (+2 signature changes, +6 parameter additions)
   - `_build_stage_a_context(config: RefinementConfig, ...)` signature
   - Pass `oversample=config.oversample` at 4 call sites
   - `_compute_panel_loss(..., config: RefinementConfig)` signature
   - Pass `oversample=config.oversample` at 2 call sites

3. **Callers of `_build_stage_a_context`** (~5 call sites to thread `config` parameter):
   - `dbex/refinement/stage_a.py` (StageA.run)
   - Possibly reconstruction helpers
   - Possibly test fixtures

### Estimated metrics:
- Lines changed: ~15-20 (1 new field, 2 signatures, 6+5 call-site updates)
- Modules touched: 3-5
- Risk: LOW (pure parameter threading, no logic changes)

## Validation Strategy

### Phase C.6: Debug validation (WITH instrumentation)
- Expect 292/292 configs with `oversample=3` (not 2/292)
- Expect ZERO "Entering auto-selection branch" messages
- Test MAY still fail if oversample wasn't the only issue (but should show progress)

### Phase C.7: Clean validation (WITHOUT instrumentation)
- Remove debug prints from nanobrag_torch
- Rerun DB-AT-028/029
- Expect both PASS:
  - DB-AT-028: chi²/pixel initial ≤ 1e2
  - DB-AT-029: median ROI correlation before ≥ 0.2

## Next Actions for Ralph

1. **Add oversample field** to RefinementConfig (trivial)
2. **Thread config parameter** through `_build_stage_a_context` call chain (find all callers, add param)
3. **Update 6 create_detector_config calls** to pass `oversample=config.oversample`
4. **Debug validation** to confirm 292/292 configs (keep nanobrag debug prints for now)
5. **Clean validation** to confirm tests PASS (remove debug prints, final check)

## Risk Assessment

**What could still go wrong after this fix?**

1. **Oversample wasn't the only problem**: Fix improves config consistency but DB-AT-028/029 still fail
   - Mitigation: Debug logs will show whether auto-selection is eliminated
   - Escalation: If oversample=3 preserved everywhere but tests still fail, marks issue for spec_change consideration

2. **Threading breaks existing tests**: Adding `config` parameter to `_build_stage_a_context` breaks callers
   - Mitigation: Comprehensive test validation (Stage A expansion + smoke tests)
   - Rollback: Simple git revert if tests regress

3. **Oversample=3 is wrong value**: Default 3 may not be appropriate for all cases
   - Mitigation: Can adjust `RefinementConfig` default or add override logic
   - Note: Phase A debug shows explicit `oversample=3` somewhere, so that's the target value

## Design Health Check

This fix is **architecture-compliant** (not a code smell):
- `oversample` belongs in `RefinementConfig` (global simulation parameter)
- Threading through warm context is correct separation of concerns
- Consolidates config lifecycle management

After this fix, ALL detector configs will inherit `oversample` from the job-level `RefinementConfig`, maintaining consistency across panel/ROI modes and warm/cold paths.

## Lifecycle State

- **Phase A**: Complete (debug instrumentation, root cause MISIDENTIFIED)
- **Phase B**: Complete but INSUFFICIENT (deep copy fix technically correct but strategically incomplete)
- **Phase C**: PLANNING (this loop)
- **Next loop**: Implementation (thread config.oversample through warm simulator creation)
