# ARCH-IMPL-CONFORMANCE-001 Phase B.5: Debug Cold-Path Test Hang

## Date: 2026-01-14T060000Z
## Loop: i=113 (Galph planning)

## Context

Loop i=112 (Ralph) completed Phase B.3-B.4 implementation:
- ✅ Stage A refactored to use canonical `apply_sqrt_spot_scale` API (stage_a.py:438-450)
- ✅ Reconstruction refactored to use canonical API (reconstruction.py:501-509)
- ✅ Phase A.1 warm-cache test: PASSED (9.57s)
- ❌ Phase A.2 cold-path test: HUNG (>2.5min, test timeout)
- ⚠️ Stage A smoke test: SKIPPED (selector error in input.md)

**Code review** (commit 6fa924b9):
- Implementation looks correct
- Canonical API properly applied at all multiplication sites
- Torch ↔ numpy conversion preserves device/dtype
- No obvious logic bugs

**Problem**: Phase A.2 test hung, blocking validation of Phase B.3-B.4 refactor.

## Analysis

### Hypothesis 1: Test Is Slow But Working
**Likelihood**: MEDIUM
**Evidence**:
- Cold-path reconstruction creates simulators from scratch (no warm cache)
- Simulator instantiation + HKL grid setup is expensive
- Default pytest timeout may be too short for cold path

**Test**: Run Phase A.2 with extended timeout (600s / 10min)

### Hypothesis 2: Infinite Loop / Deadlock
**Likelihood**: LOW
**Evidence**:
- Code review shows no obvious infinite loops
- Stage A uses same canonical API and works fine
- Reconstruction logic is structurally similar to warm-cache path (which works)

**Test**: If extended timeout still hangs, add minimal print instrumentation to identify stall location

### Hypothesis 3: Environment / Fixture Issue
**Likelihood**: LOW-MEDIUM
**Evidence**:
- Test collection succeeded (fixture data exists)
- Warm-cache test passes (fixture/calibration data is valid)
- Cold path uses same fixtures but different code path

**Test**: Instrumentation would reveal if stuck loading fixtures

## Diagnostic Plan

### Step 1: Extended Timeout (Primary Diagnostic)

**Rationale**: Rule out slow-but-working execution before adding instrumentation.

**Command**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv --timeout=600 \
  tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path
```

**Expected outcomes**:
- **PASS**: Test was just slow; update with `@pytest.mark.timeout(600)` decorator, document runtime
- **FAIL with error**: Actual bug; analyze stack trace, fix if simple config issue
- **HANG again**: Proceed to Step 2 (instrumentation)

### Step 2: Minimal Instrumentation (If Still Hangs)

**Scope**: Add print statements only around simulator instantiation in reconstruction cold path

**Target locations** (reconstruction.py):
- Before `create_unified_simulator` call (~line 310)
- After simulator creation, before `.run()` (~line 320)
- After `.run()`, before `apply_sqrt_spot_scale` (~line 490)
- After canonical API call (~line 509)

**Rationale**: Identify where execution stalls without creating shadow pipeline

**Example instrumentation**:
```python
print(f"[DEBUG] Panel {pid}: Creating simulator...")
simulator, normalized_mask, sqrt_scale_from_factory, metadata = create_unified_simulator(...)
print(f"[DEBUG] Panel {pid}: Simulator created, running...")
bragg_panel = sim.run()
print(f"[DEBUG] Panel {pid}: Simulator.run() complete, mean={bragg_panel.mean().item():.6e}")
```

### Step 3: Decision Tree

```
Extended timeout test →
├─ PASS:
│  ├─ Update test with @pytest.mark.timeout(600)
│  ├─ Document expected runtime in summary
│  └─ Proceed to Phase B.6 (docs update)
│
├─ FAIL (with error):
│  ├─ Capture full stack trace
│  ├─ Analyze root cause
│  ├─ Fix if simple config issue (e.g., missing parameter)
│  └─ If deeper bug: revert to Phase B.3-B.4 and revise
│
└─ HANG again:
   ├─ Add minimal instrumentation (Step 2)
   ├─ Rerun with extended timeout
   ├─ Document stall location
   └─ Assess unblock options:
      ├─ Environment blocker: mark Phase A.2 as deferred, assess if Phase A.1 warm-cache PASS is sufficient
      ├─ Implementation bug: debug and fix
      └─ Test design issue: revise Phase A.2 test scope
```

## Non-Negotiables Compliance

### Dwell Tracking
- Last 3 loops for ARCH-IMPL-CONFORMANCE-001:
  - i=110: planning (Phase B.1-B.2 planning)
  - i=111: implementation (Phase B.1-B.2 implementation)
  - i=112: implementation (Phase B.3-B.4 implementation)
- **This loop (i=113): debug** (evidence-only to unblock validation)
- **Next loop must be**: validation (if unblocked) or switch focus (if blocked)

### Evidence→Action Contract
Must end with either:
1. Phase A.2 PASS (validation complete, proceed to Phase B.6), OR
2. Documented blocker + focus switch decision

### No Stacking on Unknown
If extended timeout still hangs and instrumentation doesn't reveal root cause within this loop:
- Mark Phase A.2 as environment blocker
- Assess if Phase A.1 warm-cache PASS is sufficient for Phase B exit criteria
- Do NOT add more diagnostic loops; switch focus or escalate

### Probe Freeze
No plan-local diagnostic scripts. All instrumentation inline (print statements only).

## Artifacts Plan

**Artifacts root**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T060000Z/`

Files to create:
- `pytest_phase_a2_extended_timeout.log` — Primary diagnostic with 600s timeout
- `pytest_phase_a1_regression_check.log` — Warm-cache regression (should still PASS)
- `debug_analysis.md` — Analysis of diagnostic results
- `summary.md` — Loop summary with next action

## Exit Criteria for This Loop

Loop i=113 succeeds if it produces:
1. **Definitive test outcome** (PASS, FAIL with error, or documented hang location)
2. **Next action decision** (Phase B.6 docs update, implementation fix, or focus switch)
3. **Artifacts** proving diagnostic was executed correctly

Loop i=113 fails if:
- No diagnostic run attempted
- Test hang not characterized (no timeout extension, no instrumentation)
- No next action decision documented

## Risk Assessment

### Low Risk
- **Extend timeout**: Safe, reversible, doesn't change production code
- **Minimal instrumentation**: Print statements only, no logic changes

### Medium Risk
- **Test may still hang with 10min timeout**: Would indicate deeper issue (infinite loop, deadlock)
- **Mitigation**: Instrumentation would identify stall location

### High Risk (Avoided)
- **Adding complex diagnostic probes**: Violates PROBE-FREEZE-001
- **Changing production logic to "fix" hang**: Stacking on unknown
- **Multiple debug loops without progress**: Violates dwell enforcement

## Cross-References

- **Phase B.3-B.4 implementation**: commit 6fa924b9
- **Phase B.3-B.4 planning**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/phase_b3_b4_planning.md`
- **Implementation plan**: `plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md`
- **Canonical API**: `dbex/refinement/scaling_utils.py:35-111`
- **Reconstruction cold path**: `dbex/refinement/reconstruction.py:302-320, 490-509`
- **Phase A.2 test**: `tests/architecture/test_scale_contracts.py:232-305`

---

**Phase B.5 planning complete. Ready for debug loop i=113 (Ralph).**
