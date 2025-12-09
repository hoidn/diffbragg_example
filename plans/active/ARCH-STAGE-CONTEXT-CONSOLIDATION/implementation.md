# ARCH-STAGE-CONTEXT-CONSOLIDATION Implementation Plan

**ID:** ARCH-STAGE-CONTEXT-CONSOLIDATION
**Title:** Stage Context Parameter Consolidation
**Owner:** Galph ↔ Ralph
**Status:** pending

## Normative References
- docs/architecture.md
- dbex/refinement/context.py (existing context dataclasses)
- dbex/refinement/stage_a.py::_build_stage_a_params (13 positional args)
- dbex/refinement/stage_b.py::_build_stage_b_params (15 positional args)
- dbex/refinement/stage_c.py::_build_stage_c_params

## Exit Criteria (Binary Pass/Fail)

1. **Stage A/B/C `_build_*_params` accept single typed context parameter**
   - Validation: Grep for `def _build_stage_a_params`, count parameters
   - Pass: ≤3 parameters (self, config, context)

2. **Telemetry updates use dataclass property assignment or setter methods**
   - Validation: No `telemetry_dict["key"] = value` mutations
   - Pass: All telemetry updates via `telemetry_state.field = value`

3. **Enforcement test validates context immutability guarantees**
   - Validation: `pytest tests/architecture/test_stage_context_contracts.py`
   - Pass: Test exists and passes

4. **All existing Stage A/B/C smoke tests continue to pass**
   - Validation: `pytest tests/dbex/test_torch_refine_smoke.py -v`
   - Pass: Same tests pass as before refactoring

## Phases

### Phase A: Analyze Current Signatures (Galph-only, i=251)

**A.1** Catalog all parameters in `_build_stage_a_params`, `_build_stage_b_params`, `_build_stage_c_params`
**A.2** Identify parameters that already exist in context dataclasses vs need to be added
**A.3** Draft extended context dataclass schema

**Exit:** Summary report in `reports/2025-12-08T230500Z/signature_analysis.md`

### Phase B: Extend Context Dataclasses

**B.1** Add missing fields to `StageAInputContext`, `StageBInputContext`, `StageCInputContext` in `context.py`
**B.2** Ensure all fields have appropriate defaults (for backwards compatibility)
**B.3** Add property accessors or setter methods for telemetry state updates

**Exit:** Updated `dbex/refinement/context.py` with extended dataclasses

### Phase C: Refactor Stage Helper Signatures

**C.1** Update `_build_stage_a_params` to accept single `context: StageAInputContext`
**C.2** Update `_build_stage_b_params` to accept single `context: StageBInputContext`
**C.3** Update `_build_stage_c_params` to accept single `context: StageCInputContext`
**C.4** Update all call sites in `StageA.run`, `StageB.run`, `StageC.run`

**Exit:** All `_build_*_params` have ≤3 parameters

### Phase D: Eliminate Dict Mutations

**D.1** Replace `telemetry_dict["key"] = value` patterns with dataclass setters
**D.2** Ensure telemetry state flows through typed channels only

**Exit:** No dict mutation patterns in Stage B baseline parity guard

### Phase E: Add Enforcement Test

**E.1** Create `tests/architecture/test_stage_context_contracts.py`
**E.2** Test that context dataclasses have required fields
**E.3** Test that telemetry updates use typed paths (mock-verify no dict mutations)

**Exit:** Enforcement test passes

## Dependency Analysis

- **Depends on:** ARCH-REFACTOR-001 ✓ (Stage helpers own their logic)
- **Blocks:** None (tech debt cleanup)
- **Risk:** Medium (signature changes propagate to multiple call sites)

## Abort/Escalation Trigger

If Phase C changes cause >5 test failures unrelated to the refactoring (regressions), pause and investigate before continuing.
