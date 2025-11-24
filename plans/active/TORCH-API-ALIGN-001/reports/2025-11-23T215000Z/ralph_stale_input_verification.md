# Ralph Stale Input Verification — TORCH-API-ALIGN-001 Phase B3

**Date:** 2025-11-23 (current loop i=247)
**Actor:** Ralph
**Status:** WORK ALREADY COMPLETE — Stale input detected

## Executive Summary

**Finding:** The work requested in `input.md` (Phase B3 tolerance sweep experiment) was **ALREADY COMPLETED** in a prior Ralph loop (commit 97879da, 2025-11-23T215000Z).

**Evidence:**
- Tolerance sweep JSON exists and contains complete results
- Test log exists with full instrumentation output
- Decision.md exists with Path C analysis
- Git history shows completion commit `97879da`
- Galph follow-up commit `3219c37` shows supervisor already reviewed and rescoped

**Recommendation:** Input.md is stale. No additional work required for Phase B3 tolerance analysis. Initiative should proceed per Galph's rescope decision (factory-only path).

## Verification Checklist

### Requested Work (from input.md)

**Step 1: Add Instrumentation to Test** ✓ COMPLETE
- Location: `tests/dbex/test_experiment_parity.py::test_parity_small_fixture`
- Lines 153-178: Debug output (detector config, HKL grid, A*)
- Lines 164-178: Tolerance sweep loop (7 tolerances)
- Lines 180-208: JSON save logic
- Lines 210-216: Statistics output
- Lines 217-223: Parity assertion with adjusted tolerance

**Step 2: Save Tolerance Sweep Results** ✓ COMPLETE
- File: `plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T215000Z/tolerance_sweep.json`
- Content: Complete sweep summary with 7 tolerance levels, outlier counts, max_abs_diff, MSE

**Step 3: Adjust Assertion** ✓ COMPLETE
- Line 220: `TOLERANCE = 1e-04` (adjusted from 1e-06)
- Lines 222-223: Updated assertion message with evidence reference

**Step 4: Run Test with Instrumentation** ✓ COMPLETE
- Log file: `pytest_experiment_parity_instrumented.log` (13,735 bytes)
- Command executed: `NANOBRAGG_DISABLE_COMPILE=1 pytest -vv -s tests/dbex/test_experiment_parity.py::test_parity_small_fixture`
- Test runtime: 4.20s
- Result: FAILED (max_abs_diff = 5.03e-03 > 1e-04 tolerance)

**Step 5: Decision Synthesis** ✓ COMPLETE
- File: `decision.md` (6,619 bytes)
- Path determination: **Path C** (max abs diff > 1e-03, implementation bug)
- Hypothesis ranking: H1 (boundary bug) > H2 (HKL edge case) > H3 (coordinate singularity)
- Next actions documented: diff heatmap, full instrumentation, escalation criteria

**Step 6: Write Summary** ✓ COMPLETE
- File: `summary.md` (contains Ralph's turn summary + Galph's prior summaries)
- Turn summary includes: max abs diff value, Path C verdict, next steps (diff heatmap)

**Step 7: Conditional Regression Guards** ⊘ NOT APPLICABLE
- Path A not taken (max abs diff > 1e-04, so no regression guards per input.md specification)

**Step 8: Commit** ✓ COMPLETE
- Commit: `97879da` - "TORCH-API-ALIGN-001 Phase B3: Evidence gathering — tolerance analysis BLOCKED (Path C)"
- Push: successful (visible in git log)

### Git History Evidence

```
$ git log --oneline -5
a646102 [SYNC i=247] actor=ralph status=running       ← Current loop (stale input received)
fcf51f6 [SYNC i=247] actor=galph → next=ralph status=ok galph_commit=3219c37
8bfa8d1 SUPERVISOR AUTO: reports evidence — tests: not run
3219c37 SUPERVISOR: TORCH-API-ALIGN-001 Phase B3 rescope — upstream blocker documented (tests: not run)  ← Galph rescope decision
1b83a2c [SYNC i=247] actor=galph status=running
4c7b39d [SYNC i=247] actor=ralph → next=galph status=ok ralph_commit=12205ff
12205ff RALPH AUTO: reports evidence — tests: not run
97879da TORCH-API-ALIGN-001 Phase B3: Evidence gathering — tolerance analysis BLOCKED (Path C)  ← Ralph completion commit
```

**Timeline:**
1. Ralph completed tolerance sweep (commit `97879da`)
2. Ralph committed evidence artifacts and pushed
3. Galph reviewed evidence (loop i=247)
4. Galph made rescope decision (commit `3219c37`)
5. Galph committed rescope and pushed
6. **Current loop:** Ralph received stale input.md requesting work already done in step 1

### Artifact Verification

All artifacts exist and contain expected content:

```
$ ls -lh plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T215000Z/
total 68K
-rw-rw-r-- 1 ollie ollie  648 Nov 23 21:09 analysis_run.log
-rw-rw-r-- 1 ollie ollie 6.5K Nov 23 21:13 decision.md                          ← Path C decision analysis
-rw-rw-r-- 1 ollie ollie 7.2K Nov 23 21:09 evidence_analysis.md                 ← Galph's prior analysis
-rw-rw-r-- 1 ollie ollie  14K Nov 23 21:23 phase_b3_rescope_decision.md         ← Galph's rescope decision
-rw-rw-r-- 1 ollie ollie  14K Nov 23 21:24 pytest_experiment_parity_instrumented.log  ← Test execution log
-rw-rw-r-- 1 ollie ollie 2.3K Nov 23 21:23 summary.md                           ← Turn summaries (Ralph + Galph)
-rw-rw-r-- 1 ollie ollie 1.1K Nov 23 21:24 tolerance_sweep.json                 ← Sweep results
```

**File integrity:**
- `tolerance_sweep.json`: Contains max_abs_diff=0.005025771912187338, MSE=2.4088e-11, 7 tolerance results
- `decision.md`: 151 lines, complete Path C analysis with hypothesis ranking
- `pytest_experiment_parity_instrumented.log`: 13,735 bytes, full pytest output with instrumentation
- `summary.md`: Contains 3 turn summaries (Ralph 215000Z, Galph 215000Z, Galph prior)
- `phase_b3_rescope_decision.md`: 14,060 bytes, Galph's complete rescope decision

### Current Test State Verification

Re-ran test to confirm current state matches prior evidence:

```
$ pytest -vv -s tests/dbex/test_experiment_parity.py::test_parity_small_fixture
...
[INSTRUMENTATION]
  max_abs_diff=5.03e-03, MSE=2.41e-11
  Tolerance 1.0e-06: FAIL (outliers=1/1048576, 0.000%)
  ...
  Tolerance 1.0e-03: FAIL (outliers=1/1048576, 0.000%)

FAILED
AssertionError: Parity FAIL: max abs diff 5.03e-03 > 1.0e-04 tolerance
```

**Result:** Identical to prior run (max_abs_diff=5.03e-03, 1 outlier pixel, Path C)

## Conclusion

**All requested work is complete.** The input.md specification was already executed in full by a prior Ralph loop, reviewed by Galph, and escalated to rescope decision.

**Phase B3 Status (per Galph's decision):**
- Exit Criterion #3 **RESCOPED** (not FAILED)
- Blocker documented (ARCH-FACTORY-003 finding)
- Initiative proceeds with factory-only path
- ExperimentModel adapter marked experimental/deferred pending upstream fix

**Next Action (per Galph's rescope decision):**
- Validate Phase A1 (DIALS mapping parity) with factory path OR
- Skip to Phase D4 seam decision (factory-only path chosen, complete docs/rollout, close initiative)

**Recommendation:** Ralph should NOT repeat the tolerance sweep work. Instead, acknowledge completion and return to supervisor for next focus selection.

## References

- Prior Ralph loop commit: `97879da` (2025-11-23T215000Z)
- Galph rescope commit: `3219c37` (2025-11-23T~19:00:00Z)
- Artifacts directory: `plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T215000Z/`
- Evidence files: `tolerance_sweep.json`, `decision.md`, `pytest_experiment_parity_instrumented.log`
- Rescope decision: `phase_b3_rescope_decision.md`

---

**Verification completed:** 2025-11-23 (current loop i=247)
**Verified by:** Ralph (stale input detection protocol)
