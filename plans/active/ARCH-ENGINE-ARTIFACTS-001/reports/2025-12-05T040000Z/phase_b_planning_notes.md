# Phase B Planning Notes — ARCH-ENGINE-ARTIFACTS-001
## Loop: 2025-12-05T040000Z
## Actor: Galph (Supervisor)

## Summary
Phase B focuses on **validation**, not implementation. Both Stage B and Stage C already emit `bragg_full` artifacts when terminal, but we need parity tests to prove the artifact path matches the reconstruction helper path within ≤1e-6 relative MSE.

## Current State Analysis

### Artifact Emission (Already Complete)

**Stage A (lines 2022-2051 of stage_a.py):**
- Conditionally calls `build_final_bragg_from_stage_a_telemetry` when terminal
- Populates `StageAArtifacts.bragg_full`

**Stage B (lines 1687-1730 of stage_b.py):**
- Conditionally calls `build_final_bragg_from_stage_b_telemetry` when terminal (Stage C disabled)
- Populates `StageBArtifacts.bragg_full`
- Respects CPU fallback mode (GRADIENT-003)

**Stage C (lines 1150-1726 of stage_c.py):**
- Always populates `StageCArtifacts.bragg_full` (Phase A.3 confirmed)
- Converts torch tensor to CPU numpy inside `_run_lbfgs` before returning

### Orchestrator Consumption (Already Has Fallback Logic)

**dbex/nanobrag_refinement.py:**
- Lines 227-245: Stage A artifact-first with helper fallback
- Lines 368-427: Stage B artifact-first with helper fallback
- Lines 509-512: Stage C artifact-only (no helper fallback)

### Gap: No Parity Tests

**Missing validation:**
- No test proves Stage A artifact matches helper output
- No test proves Stage B artifact matches helper output (Exit Criterion #2)
- Stage C has no legacy helper path to compare against

**Why this matters:**
- Exit Criterion #2 requires ≤1e-6 relative MSE parity
- Without tests, we can't confidently remove the fallback branches in Phase C
- Stage B is especially critical because it has CPU fallback mode

## Phase B Scope

### B0: Baseline Snapshot ✅ (Can reuse from Phase A.0)
Already captured `test_stage_b_shell_modifiers` and `test_stage_c_detector_microslip` collect-only logs.

### B1: Stage B Implementation (Already Done!)
Stage B already calls `build_final_bragg_from_stage_b_telemetry` when terminal (commit from ARCH-STAGE-CONTEXT-001 Phase D).

**No work needed for B1.**

### B2: Parity Harness (THIS IS THE REAL WORK)

**Goal:** Prove artifact path produces identical output to helper path.

**Strategy:**
Create a new test file `tests/dbex/test_artifact_parity.py` with:

1. **Stage A parity test:**
   - Run refinement with only Stage A enabled (is_terminal=True)
   - Capture `bragg_full` from artifact
   - Call `build_final_bragg_from_stage_a_telemetry` directly with same inputs
   - Assert `np.allclose(artifact_bragg, helper_bragg, rtol=1e-6)`

2. **Stage B parity test:**
   - Run refinement with Stage A+B enabled, Stage C disabled (B is terminal)
   - Capture `bragg_full` from Stage B artifact
   - Call `build_final_bragg_from_stage_b_telemetry` directly with same inputs
   - Assert `np.allclose(artifact_bragg, helper_bragg, rtol=1e-6)`
   - **Must cover both shell mode and per-reflection mode**
   - **Must cover CPU fallback mode (GRADIENT-003)**

**Test fixtures needed:**
- Small detector configs (reuse from existing smokes)
- `refGeom_small` or `refGeom_medium` datasets
- Both shell and per-reflection hkl_metadata variants

**Validation:**
- Tests PASS with ≤1e-6 relative MSE
- CPU fallback path also PASSES
- Captures logs under `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T040000Z/`

### B3: Stage C Telemetry Cleanup (Already Done!)

Stage C never put `bragg_full` in telemetry dict—it's always been artifact-only.

**Verification needed:**
Check that `RefinementTelemetry` dataclass (dbex/refinement/stage.py) doesn't have a `bragg_full` field.

**No work needed for B3.**

## Risks & Mitigations

### Risk: Parity tests fail due to legitimate differences
**Likelihood:** Medium
**Impact:** High (would block Phase C orchestrator cleanup)
**Mitigation:**
- Start with Stage A parity (simpler)
- Add debug instrumentation to show where divergence occurs
- May need to adjust tolerance or identify root cause

### Risk: CPU fallback mode has different numerics
**Likelihood:** Medium (known concern from GRADIENT-003)
**Impact:** Medium (may need separate tolerance for CPU mode)
**Mitigation:**
- Use separate test for CPU fallback
- Document any tolerance adjustments
- May need to relax to ≤1e-5 for CPU mode

### Risk: Per-reflection mode reconstruction is broken
**Likelihood:** Low (reconstruction helper exists, but untested)
**Impact:** High (would block TORCH-REFINE-004 completion)
**Mitigation:**
- Test both shell and per-reflection modes
- Can mark per-reflection test as xfail if needed and create separate initiative

## Next Steps (for input.md)

**Do Now for Ralph:**

1. Create `tests/dbex/test_artifact_parity.py` with two test functions:
   - `test_stage_a_artifact_matches_helper`: Stage A-only refinement parity
   - `test_stage_b_artifact_matches_helper_shell_mode`: Stage B shell mode parity

2. Each test should:
   - Use `refGeom_small` dataset (small detector for speed)
   - Build configs via standard helpers
   - Run refinement via `RefinementEngine` directly (not facade)
   - Extract artifact bragg_full
   - Call reconstruction helper with same inputs
   - Assert `np.allclose(artifact, helper, rtol=1e-6, atol=0)`
   - Print max absolute diff and relative MSE for diagnostics

3. Validation:
   - Run: `pytest -vv tests/dbex/test_artifact_parity.py`
   - Capture log: `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T040000Z/pytest_parity.log`
   - If tests fail, capture debug diagnostics (shape, dtype, mean, max, argmax diffs)

4. Document:
   - Update implementation.md Phase B checklist (B2 complete)
   - Note in summary.md: "Phase B parity validation complete" or "Phase B blocked: parity failed"

**Success Criteria:**
- Both tests PASS with ≤1e-6 relative MSE
- Logs show artifact and helper outputs are numerically identical
- Ready for Phase C orchestrator cleanup

**If Parity Fails:**
- Do NOT proceed to Phase C
- Create debug artifacts showing divergence points
- May need separate initiative to fix reconstruction helpers

## Files to Create
- `tests/dbex/test_artifact_parity.py` (new test module, ~200 lines)

## Files to Read (for test implementation)
- `dbex/refinement/stage_a.py` (artifact emission pattern)
- `dbex/refinement/stage_b.py` (artifact emission pattern)
- `dbex/refinement/reconstruction.py` (helper signatures)
- `tests/dbex/test_torch_refine_smoke.py` (fixture patterns to reuse)

## Spec/Finding Citations
- docs/spec-db-workflow.md §§33-45 (engine contract)
- REFINE-FLOW-001 (Stage B baseline parity)
- GRADIENT-003 (CPU fallback constraints)
- ARCH-ENGINE-ARTIFACTS-001 Exit Criterion #2 (≤1e-6 relative MSE)

## Expected Outcome
- Phase B parity tests added and passing
- Confidence that artifact path is correct
- Ready to remove fallback branches in Phase C
- Or: identify that reconstruction helpers need fixing before Phase C

## Artifacts Inventory
- `phase_b_planning_notes.md` — This file ✅
- `pytest_parity.log` — Parity test execution (pending Ralph implementation)
- `summary.md` — Loop summary (pending end-of-loop)
