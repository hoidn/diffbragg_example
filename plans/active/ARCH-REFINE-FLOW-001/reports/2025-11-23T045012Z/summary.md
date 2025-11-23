# Phase B1b Planning Summary — StageA Wrapper Handoff

**Loop:** i=195 (Galph planning)
**Date:** 2025-11-23T045012Z
**Initiative:** ARCH-REFINE-FLOW-001 Phase B1b — StageA Wrapper Implementation
**Mode:** Planning (ready_for_implementation handoff)

## Context

Phase B1a-loop3 is COMPLETE (commit caa510e, 2025-11-23T060500Z):
- All 3 helpers extracted: `_build_stage_a_params`, `_build_stage_a_lbfgs_closure`, `_run_stage_a_lbfgs`
- Main function refactored (reduced by 692 lines)
- Params dict bugfix applied (params + optimizer added to param_values dict)
- Regression guard test_stage_a_expansion PASSED (12.39s)

## Problem Statement

The existing `StageA` stub (dbex/refinement/stage_a.py:61-142) is **INCORRECT**:
- It delegates back to `run_nanobrag_refinement` (line 110)
- This creates infinite recursion risk when Phase B2 wires engine delegation
- Once `run_nanobrag_refinement` calls `RefinementEngine([StageA()])`, and StageA.run() calls `run_nanobrag_refinement`, the system will loop infinitely

## Phase B1b Objective

Rewrite `StageA.run()` to:
1. Call the three extracted helpers directly (no delegation to `run_nanobrag_refinement`)
2. Package telemetry with ALL RefinementTelemetry fields + stage_type/mode per Phase A4 schema
3. Validate via compilation check + regression guard + engine contract test

## Implementation Scope

### Helper Call Sequence
```python
# STEP 1: Build parameters
helper1_result = _build_stage_a_params(crystal, detector, inputs, config, ...)

# STEP 2: Build LBFGS closure
compute_loss, closure = _build_stage_a_lbfgs_closure(param_values, telemetry_state, ...)

# STEP 3: Run LBFGS optimization
lbfgs_result = _run_stage_a_lbfgs(optimizer, closure, compute_loss, ...)

# STEP 4: Package telemetry dict
telemetry_output = {
    "optimizer": telemetry_state['optimizer'],
    ...  # All RefinementTelemetry fields
    "stage_type": "stage_a",
    "mode": "incremental_ub" | "u_matrix" | None
}
```

### Key Requirements
1. **sigma_floor_sq_cache**: Must construct tensor matching run_nanobrag_refinement pattern (single-element torch.full)
2. **Telemetry schema completeness**: Include ALL fields from dbex/refinement/stage.py:159-227 (to_dict() method)
3. **Lazy imports**: Import helpers inside run() method to avoid circular imports
4. **Device/dtype neutrality**: Extract from self._config, no hardcoded .cuda() or float32
5. **No recursion**: Do NOT call run_nanobrag_refinement

## Validation Protocol

1. **Compilation check**: `python -c "from dbex.refinement.stage_a import StageA; print('OK')"`
2. **Regression guard**: `test_stage_a_expansion` MUST PASS (inline path unchanged until Phase B2)
3. **Engine contract**: `test_engine_executes_mock_stage` MUST PASS (validates RefinementEngine protocol)

## Input.md Handoff

Authored comprehensive 10-step Do Now for Ralph (input.md):
- Review Phase B1a-loop3 artifacts
- Rewrite StageA.run() with helper orchestration (~80 lines)
- Add torch import
- Compilation check + regression guard + engine contract validation
- Update implementation.md checklist
- Write implementation summary + Turn Summary
- Commit and push

## Implementation Floor Satisfied

- Production code task: StageA.run() rewrite (~80 lines of helper orchestration)
- Validating pytest selectors:
  - `test_stage_a_expansion` (regression guard, inline path)
  - `test_engine_executes_mock_stage` (engine contract validation)

## Dwell Enforcement

- Last loop: review_or_housekeeping (B1a-loop3 blocker review)
- This loop: ready_for_implementation (Phase B1b wrapper implementation)
- Dwell: 0 (reset after B1a completion milestone)
- Compliant with max-1-docs-only-loop rule

## Roadmap Alignment

- **Tier:** 2 (Architectural Maturity)
- **Initiative:** ARCH-REFINE-FLOW-001 (Protocol-based Refinement Engine)
- **Milestone:** Phase B1b (StageA wrapper)
- **Strategy:** Approved multi-loop extraction (B1a COMPLETE → B1b wrapper → B2 engine delegation)
- **Next:** Phase B2 (engine delegation in run_nanobrag_refinement) if B1b PASSES

## Findings Applied

- **PHYSICS-LOSS-001**: Telemetry schema includes chi_squared_trace_* and masked_mse_* fields
- **PHYSICS-LOSS-002**: Telemetry schema includes variance_floor_value and variance_floor_clamp_fraction
- **PHYSICS-LOSS-003**: Telemetry schema includes canonical Stage A metadata fields
- **CONVERGENCE-001**: Zero-delta bypass handled inside helper2 (transparent to wrapper)
- **GRADIENT-001**: Autograd graph preservation handled inside helper2 (transparent to wrapper)
- **GEOMETRY-003**: Baseline misset derivation handled inside helper1 (transparent to wrapper)
- **GEOMETRY-004**: Incremental UB parameterization mode detection based on config flags

## Spec Alignment

- **spec-db-workflow.md:33**: RefinementEngine SHALL accept ordered list of Stage objects (no hardcoded A→B→C)
- **spec-db-tracing.md §2**: Telemetry requirements (all RefinementTelemetry fields must be populated)
- **dbex/refinement/stage.py:23-84**: RefinementStage protocol (name, configure, run)
- **dbex/refinement/stage.py:87-227**: RefinementTelemetry dataclass (to_dict() method)

## Expected Outcomes

### Path A: All Tests PASS (expected)
- StageA.run() successfully orchestrates three helpers
- Telemetry dict includes all required fields
- Compilation PASSED, regression guard PASSED, engine contract PASSED
- **Next loop (i=196):** Galph plans Phase B2 (engine delegation in run_nanobrag_refinement)

### Path B: Compilation Failure
- Missing imports (torch, typing, dbex.nanobrag_refinement)
- Lazy import pattern incorrect
- **Action:** Ralph documents blocker → Galph reviews → debug/fix

### Path C: Regression Guard Failure
- StageA wrapper accidentally called (should NOT be called until Phase B2)
- Telemetry schema mismatch
- **Action:** Ralph documents failure signature → Galph reviews → debug/escalate

### Path D: Telemetry Schema Mismatch
- Missing required fields in telemetry_output dict
- Helper3 result structure mismatch
- **Action:** Ralph documents missing fields → Galph reviews → fix schema packaging

## Artifacts

- **Root:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/`
- **Files (to be created by Ralph):**
  - `pytest_stage_a_expansion.log` (regression guard)
  - `pytest_engine.log` (engine contract validation)
  - `phase_b1b_implementation_summary.md` (deliverables summary)
  - `summary.md` (Turn Summary block)

## Commit Message Template

```
ARCH-REFINE-FLOW-001 Phase B1b: StageA wrapper implementation — tests: not run

- Rewrote StageA.run() to call extracted helpers directly (no recursion)
- Telemetry packaging includes all RefinementTelemetry fields + stage_type/mode
- Compilation PASSED, regression guard PASSED (inline path unchanged)
- Phase B1b COMPLETE, ready for Phase B2 engine delegation
```

## Next Actions

**Ralph (i=195):** Execute Phase B1b implementation per input.md Do Now (10 steps)

**Galph (i=196):** If B1b PASSES → Plan Phase B2 (engine delegation in run_nanobrag_refinement)
- Detect Stage-A-only mode (not enable_stage_c)
- Instantiate RefinementEngine([StageA()])
- Delegate to engine.run()
- Keep Stage B/C inline temporarily
- Regression guard MUST PASS

If B1b BLOCKED → Review Ralph's blocker report and decide escalation path.

---

### Turn Summary
Planned Phase B1b StageA wrapper implementation after confirming B1a-loop3 bugfix success.
Identified existing StageA stub creates infinite recursion risk; authored Do Now directing direct helper orchestration (no run_nanobrag_refinement delegation).
Telemetry packaging requires all RefinementTelemetry fields + stage_type/mode per Phase A4 schema.
Next: Ralph implements StageA.run() wrapper calling three extracted helpers (compilation + regression + contract validation).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/ (input.md)
