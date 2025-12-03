# Phase A Planning Notes — ARCH-ENGINE-ARTIFACTS-001
## Loop: 2025-12-05T030000Z
## Actor: Galph (Supervisor)

## Summary
Phase A kickoff for artifact channel wiring. Infrastructure from ARCH-STAGE-CONTEXT-001 Phase B.1/D already exists; this initiative wires Stage B/C to populate `bragg_full` fields and updates orchestrator to consume artifacts instead of calling reconstruction helpers.

## Current State Analysis

### Infrastructure Already in Place (ARCH-STAGE-CONTEXT-001)
✅ **Engine side:**
- `RefinementEngine._artifacts` dict (engine.py:68, 120, 157)
- `engine.artifacts` property (engine.py:274)
- Engine resets artifacts per run, propagates between stages

✅ **Artifacts dataclasses exist:**
- `StageAArtifacts` with `bragg_full` field (artifacts.py:26-50)
- `StageBArtifacts` with `bragg_full` field (artifacts.py:52-94)
- `StageCArtifacts` with `bragg_full` field (artifacts.py:98-113)

✅ **Stage A already populates bragg_full when terminal:**
- stage_a.py:2022-2051 checks `is_terminal_stage` and calls `build_final_bragg_from_stage_a_telemetry`
- Artifacts passed via `StageResult` (ARCH-TELEMETRY-001 Phase C.2)

### Gaps to Close

❌ **Stage B doesn't populate bragg_full:**
- `StageBArtifacts.bragg_full` field exists but always None
- Reconstruction helper `build_final_bragg_from_stage_b_telemetry` exists (reconstruction.py:269-520) but not called from Stage B

❌ **Stage C doesn't populate bragg_full:**
- `StageCArtifacts.bragg_full` field exists but always None
- Stage C run() method doesn't call any reconstruction helper
- Stage C directly stores bragg tensors internally but doesn't expose via artifacts

❌ **Orchestrator still uses branch logic:**
- `run_nanobrag_refinement` (dbex/nanobrag_refinement.py) has manual stage-specific branches
- Calls reconstruction helpers directly instead of reading engine.artifacts

## Phase A Scope

### A0: Baseline snapshot ✅ COMPLETE
- Ran `pytest --collect-only` for Stage B/C smokes
- 2/6 tests collected (both selectors healthy)
- Log: `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T030000Z/baseline_collect_only.log`

### A1: Design artifact API (IDL sketch)
**Decision: NO NEW API NEEDED**

The artifact channel already exists and works correctly:
- Engine exposes `engine.artifacts[stage_name]` read-only dict
- Stages return `StageResult(telemetry=..., artifacts=...)`
- Artifacts dataclasses already have `bragg_full` fields with correct types/documentation

**Required changes are wiring only:**
1. Stage B: call reconstruction helper, store result in `bragg_full` field
2. Stage C: extract final bragg from run, store in `bragg_full` field
3. Orchestrator: read `engine.artifacts[final_stage_name].bragg_full` instead of calling helpers

**Documentation updates:**
- Update implementation.md Phase A checklist (A1 becomes "Artifact API review" noting infrastructure exists)
- Add note to `docs/architecture/module_map.md` that Stage B/C now emit bragg_full artifacts
- Update `dbex/refinement/artifacts.py` docstrings to clarify Stage B/C now populate bragg_full unconditionally (not just when terminal)

### A2: Implement artifact registry
**Decision: SKIP - Already exists**

Engine artifact registry fully implemented in ARCH-STAGE-CONTEXT-001 Phase B.1:
- `_artifacts` dict on engine
- Populated from `StageResult.artifacts` (engine.py:149-157)
- Read-only `artifacts` property (engine.py:270-274)
- Artifacts already serialized to telemetry_sink when set

**No implementation work required for A2.**

### A3: Update Stage C wrapper to emit bragg_full
**Scope for first implementation loop:**

1. **Stage C final bragg extraction** (dbex/refinement/stage_c.py):
   - Stage C run() already computes final bragg via `_run_lbfgs` (stage_c.py:1158-1250)
   - `bragg_full` local variable exists (line 1242) as torch tensor
   - Convert to CPU numpy before storing in artifacts:
     ```python
     bragg_full_artifact = bragg_full.cpu().numpy().astype(np.float32)
     ```
   - Update `StageCArtifacts` instantiation (line ~1260) to pass `bragg_full=bragg_full_artifact`

2. **Validation:**
   - Run `test_stage_c_detector_microslip` (small detector, panel mode)
   - Assert `engine.artifacts["stage_c"].bragg_full` is not None
   - Assert shape matches detector geometry `[n_panels, slow, fast]`
   - Assert dtype is `numpy.float32`
   - Capture test log under `2025-12-05T030000Z/pytest_stage_c_artifact.log`

3. **Documentation:**
   - Update `dbex/refinement/artifacts.py::StageCArtifacts` docstring to note bragg_full now always populated (not just when terminal)
   - Add spec citation: docs/spec-db-workflow.md §41 (stage outputs)

**Dependencies:**
- No circular import risks (artifacts.py already imports nothing heavy)
- Stage C already imports numpy (via torch)
- No new test fixtures required (existing smoke selector sufficient)

**Success Criteria:**
- Stage C smoke test PASSES
- `engine.artifacts["stage_c"].bragg_full` is numpy array
- Shape/dtype match spec (float32, [panels, slow, fast])
- Mean intensity > 0 (non-empty)

### A4 (Future): Stage B artifact emission
**Deferred to Phase B** per implementation plan.

Stage B requires more care:
- Must respect CPU fallback mode (GRADIENT-003)
- Shell modifier reconstruction is more complex than Stage C
- Parity harness needed (≤1e-6 relative MSE vs legacy helper)

Phase A focuses on Stage C as simpler proof-of-concept.

## Risks & Mitigations

### Risk: Stage C bragg_full shape mismatch
**Likelihood:** Low
**Impact:** Medium (test failure, easy to debug)
**Mitigation:** Stage C already validates panel shapes internally; artifact is just exposing existing tensor

### Risk: Memory overhead from artifact storage
**Likelihood:** Low
**Impact:** Low (engine already stores artifacts, just adding numpy array)
**Mitigation:** bragg_full is CPU-resident numpy (not GPU tensor), matches existing Stage A pattern

### Risk: Selector fragility (small-detector only)
**Likelihood:** Low
**Impact:** Low (test isolation)
**Mitigation:** `test_stage_c_detector_microslip` is well-established, runs reliably per recent fix-plan attempts

## Next Steps (for input.md)

**Do Now for Ralph:**
1. Update `dbex/refinement/stage_c.py::StageC.run()`:
   - After `_run_lbfgs` returns `bragg_full` tensor (line ~1242)
   - Convert to CPU numpy: `bragg_full_artifact = bragg_full.cpu().numpy().astype(np.float32)`
   - Pass to `StageCArtifacts(bragg_full=bragg_full_artifact)` (line ~1260)

2. Update `dbex/refinement/artifacts.py::StageCArtifacts` docstring:
   - Change "Replaces engine._stage_c_bragg_full private attribute" → "Always populated by Stage C; replaces engine._stage_c_bragg_full"
   - Add normative requirement: "Stage C MUST populate this field unconditionally (not just when terminal)"
   - Cite docs/spec-db-workflow.md §41

3. Validate:
   - Run: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
   - Capture log: `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T030000Z/pytest_stage_c_artifact.log`
   - Add assertion in test or inspect via debugger: `engine.artifacts["stage_c"].bragg_full is not None`

4. Document:
   - Update `plans/active/ARCH-ENGINE-ARTIFACTS-001/implementation.md` Phase A checklist (A3 complete)
   - Note in summary.md: "Phase A.3 complete: Stage C now emits bragg_full artifact"

**Expected Outcome:**
- Test PASSES (no behavioral change, just artifact exposure)
- Artifact populated with correct shape/dtype
- Ready for Phase B (Stage B artifact emission) in next loop

## Files to Touch
- `dbex/refinement/stage_c.py` (~5 lines: convert tensor, pass to artifacts)
- `dbex/refinement/artifacts.py` (docstring update, ~3 lines)
- Test inspection (no test code changes required for Phase A.3)

## Spec/Finding Citations
- docs/spec-db-workflow.md §41 (stage contract + outputs)
- docs/spec-db-core.md §§85-90 (Bragg tensor contracts)
- ARCH-STAGE-CONTEXT-001 (artifact channel infrastructure)
- ARCH-ENGINE-003 (telemetry enrichment must stay in active engine path)

## Artifacts Inventory
- `baseline_collect_only.log` — Phase A.0 selector health check ✅
- `phase_a_planning_notes.md` — This file ✅
- `pytest_stage_c_artifact.log` — Phase A.3 validation (pending Ralph implementation)
- `summary.md` — Loop summary (pending end-of-loop)
