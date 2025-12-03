# Galph Loop 468 Analysis - DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C Review

## Summary
Phase C config lifecycle fix successfully propagated oversample=3 to all 292 DetectorConfig instances, resolving the auto-selection issue. However, exit criteria validation reveals a deeper blocker: simulator producing all-zero Bragg output despite correct scale factors.

## Phase C Implementation Review

### What Ralph Delivered (commit aa74003e)
✅ Added `RefinementConfig.oversample` field (default=3)
✅ Threaded `config` parameter through `_build_stage_a_context` and `_compute_panel_loss`
✅ Passed `oversample=oversample_value` to all 4 `create_detector_config` call sites
✅ Updated callers in `stage_a.py` and `stage_b.py`

### Debug Validation Results (with nanobrag instrumentation)
✅ 292/292 DetectorConfig instances have `oversample=3` (was 2/292 in Phase B)
✅ 0 instances of `oversample=-1`
✅ 0 auto-selection events
✅ Config lifecycle working correctly

### Regression Check
⚠️ `test_stage_a_expansion` FAILED - but pre-existing issue (also fails on parent commit aa74003e~1)
- Not a regression from oversample fix
- Root cause: Zero simulator output (same as DB-AT-028 blocker below)

## Exit Criteria Validation - BLOCKED

### DB-AT-028/029 Status
**Test Status**: Runs but produces zero Bragg output
**Expected**: chi²/pixel initial ≤ 1e2, median ROI correlation ≥ 0.2
**Actual**: Test completes but Bragg tensor all zeros → automatic skip/fail

### Critical Evidence from Debug Run
```
[ARCH-SIM-CONSTRUCTION-001 DEBUG]
  log_scale_baseline_value: 20.138489594990745
  log_scale (param_deltas_a): 0.0
  delta_bound: 3.0
  scale_factor (after exp): 557230080.0          ← CORRECT (exp(20.138) ≈ 5.57e8)
  sqrt_spot_scale: 557230532.6778347
  spot_scale_override: 3.105058665484234e+17
  bragg_panel[0] mean (raw sim output): 0.000000e+00  ← PROBLEM: should be ~1e-10
  bragg_panel[0] max: 0.000000e+00                    ← PROBLEM
  bragg_scaled[0] mean (after scale_factor): 0.000000e+00  ← Cascades from zero input
  bragg_full mean (final output): 0.000000e+00
  bragg_full max: 0.000000e+00
```

**Analysis:**
- Scale factor calculation is CORRECT (5.57e8)
- oversample parameter is CORRECT (3, not -1)
- **Simulator is running but producing zero output**
- This is the SAME core issue ARCH-SIM-CONSTRUCTION-001 was trying to fix

### Implications
The oversample fix was **necessary but insufficient**:
1. ✅ Eliminates auto-selection code path that was causing magnitude confusion
2. ❌ Does NOT resolve the underlying zero-output problem
3. Zero simulator output → zero gradients → LBFGS no-op → test_stage_a_expansion fails
4. Cannot validate DB-AT-028/029 acceptance criteria without working simulator output

## Root Cause Update

### Original Hypothesis (ARCH-SIM-CONSTRUCTION-001 Phase A-C)
"Reconstruction simulator magnitude ~23,317× too small due to oversample parameter not honored"

### Refined Hypothesis (after DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C)
"Simulator producing ZERO output. Oversample parameter was one contributing factor (now fixed), but there's a deeper initialization or configuration issue preventing Bragg tensor generation."

### Next Investigation Targets
1. **HKL grid**: Is structure factor grid populated? (check `hkl_grid.sum()`)
2. **Crystal config**: Are cell parameters / missets valid?
3. **Detector geometry**: Distance/pixel size reasonable?
4. **Beam config**: Wavelength/flux/exposure non-zero?
5. **nanobrag_torch internals**: Does `simulator.run()` actually execute diffraction calc?

## Initiative Lifecycle Decision

### DIAG-NANOBRAGG-OVERSAMPLE-001 Status
**Technical Deliverables**: ✅ COMPLETE
- Phase A debug instrumentation: ✅
- Phase B deep copy attempt: ✅ (revealed wrong root cause)
- Phase C config lifecycle fix: ✅ (292/292 oversample=3)
- All patches saved, findings documented

**Exit Criteria**: ❌ BLOCKED
- Cannot validate DB-AT-028/029 due to zero simulator output
- Cannot confirm unblocking of ARCH-SIM-CONSTRUCTION-001

**Recommendation**: Mark initiative **done** with caveats
- Scope: Diagnostics of oversample parameter handling
- Outcome: Parameter now correctly threaded through config lifecycle
- Blocker: Deeper simulator issue preventing output generation (out of scope for this diagnostics initiative)
- Next: Return to ARCH-SIM-CONSTRUCTION-001 with updated evidence

### ARCH-SIM-CONSTRUCTION-001 Status Update
**Previous Status**: stuck — blocked_environment_dependency (suspected oversample parameter issue)
**New Status**: stuck — blocked_simulator_zero_output
**New Evidence**: Oversample fix applied but simulator still produces zeros
**Next Investigation**: Expand debug instrumentation to trace why Bragg calculation produces no signal

## Findings to Document

### Update to docs/findings.md
**Finding ID**: DIAG-OVERSAMPLE-002 (new)
**Title**: Simulator Zero-Output Issue (Post-Oversample Fix)
**Severity**: Blocker (Tier 0)
**Evidence**: DB-AT-028 debug run shows bragg_panel mean/max = 0.0 despite correct scale_factor
**Impact**: Prevents validation of reconstruction helpers, blocks ARCH-SIM-CONSTRUCTION-001 and ARCH-REFACTOR-001 Phase D.3
**Root Cause**: Unknown (under investigation)
**Suspects**: HKL grid empty, crystal config invalid, detector geometry issue, or nanobrag_torch internal bug
**Mitigation**: Expand debug instrumentation to trace structure factor sampling and diffraction calculation

### DIAG-OVERSAMPLE-001 Closure Note
**Status**: Resolved → Config lifecycle fix complete
**Final State**: 292/292 DetectorConfig instances have oversample=3 (was 2/292)
**Validation**: Debug instrumentation confirmed no auto-selection events
**Caveat**: Exit criteria DB-AT-028/029 cannot be validated due to separate simulator zero-output issue (see DIAG-OVERSAMPLE-002)

## Portfolio Steering Recommendation

### Option A: Continue DIAG-NANOBRAGG-OVERSAMPLE-001 (expand scope)
Add Phase D: Investigate zero-output root cause
**Pros**: Keep diagnostic focus, leverage existing nanobrag instrumentation
**Cons**: Scope creep (initiative was oversample-focused)

### Option B: Return to ARCH-SIM-CONSTRUCTION-001 (recommended)
Mark DIAG-NANOBRAGG-OVERSAMPLE-001 done, refocus ARCH-SIM-CONSTRUCTION-001 with new evidence
**Pros**: Clearer separation of concerns, correct initiative type (architecture vs diagnostics)
**Cons**: Need to update ARCH-SIM-CONSTRUCTION-001 plan with new hypothesis

### Option C: New diagnostics initiative
Create DIAG-SIMULATOR-ZERO-OUTPUT-001
**Pros**: Clean separation, focused scope
**Cons**: Overhead of new initiative when ARCH-SIM-CONSTRUCTION-001 already exists

**Selected**: **Option B** - Return to ARCH-SIM-CONSTRUCTION-001
- More efficient (avoid initiative proliferation)
- Closer to the actual problem (reconstruction magnitude, not just oversample)
- Can leverage oversample fix as foundation for next investigation phase

## Next Actions

1. **Mark DIAG-NANOBRAGG-OVERSAMPLE-001 done** (config lifecycle fix complete)
2. **Update ARCH-SIM-CONSTRUCTION-001 status** from "blocked_environment_dependency" to "in_progress"
3. **Update ARCH-SIM-CONSTRUCTION-001 plan** with Phase D: Zero-output investigation
4. **Create input.md** for Ralph to:
   - Add HKL grid / crystal config / beam config debug instrumentation
   - Capture full forward simulation diagnostic trace
   - Identify where Bragg calculation goes to zero

## Retrospective Note (Loop Discipline)

This is the 3rd loop for DIAG-NANOBRAGG-OVERSAMPLE-001:
- Loop 1 (Phase A): Debug instrumentation revealed 290/292 oversample=-1
- Loop 2 (Phase B): Deep copy fix insufficient (config creation issue)
- Loop 3 (Phase C): Config lifecycle fix successful (292/292 oversample=3)

**Per loop discipline**: Should we continue or switch focus?
- ✅ Making progress (each loop resolved a layer)
- ✅ Phase C achieved its technical goal
- ❌ Exit criteria blocked by new issue (zero output)

**Decision**: Close initiative with "done (incomplete validation)" status and immediately switch to ARCH-SIM-CONSTRUCTION-001 for zero-output investigation. This avoids artificial initiative proliferation while maintaining clear problem tracking.
