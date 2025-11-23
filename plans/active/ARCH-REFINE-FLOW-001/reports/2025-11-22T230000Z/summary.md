### Turn Summary
Reviewed Phase C1a-loop3 completion (all 3 Stage B helpers extracted, wired, regression guard PASSED) and authored comprehensive Phase C1b Do Now directing StageB wrapper implementation mirroring StageA pattern from Phase B1b.
StageB class will call the 3 extracted helpers directly (_build_stage_b_params, _build_stage_b_lbfgs_closure, _run_stage_b_lbfgs), package telemetry with all RefinementTelemetry fields plus stage_type/mode per engine protocol, and validate via regression guard test_stage_b_shell_modifiers.
Next: Ralph executes Phase C1b implementation; if PASS → Galph plans Phase C2 (engine delegation A→B).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T230000Z/ (input.md Do Now)

---

# Phase C1b Planning Summary

## Objective
Plan and delegate StageB wrapper class implementation to Ralph, following the proven multi-loop extraction strategy from Phase B (B1a: 3-loop helper extraction → B1b: wrapper → B2: engine delegation).

## Context
Phase C1a-loop3 completed successfully (commit ed30183, artifacts 2025-11-22T070000Z):
- Extracted 3 Stage B helpers (~600+ lines total):
  1. `_build_stage_b_params` (dbex/nanobrag_refinement.py:2087-2270, ~184 lines)
  2. `_build_stage_b_lbfgs_closure` (dbex/nanobrag_refinement.py:2273-2589, ~317 lines)
  3. `_run_stage_b_lbfgs` (dbex/nanobrag_refinement.py:2593-2708, ~118 lines)
- Wired all 3 helpers into run_nanobrag_refinement Stage B section (~610 lines → ~150 lines orchestration)
- Fixed 5 critical bugs (panel_slices, key mismatches, telemetry nested access, nanobrag_torch imports, helper3 return dict)
- Regression guard test_stage_b_shell_modifiers PASSED (exit code 0, ~14.7s runtime)

## Phase C1b Scope
Implement StageB wrapper class (dbex/refinement/stage_b.py) that:
1. Implements RefinementStage protocol (name property, configure() method, run() method)
2. Calls 3 extracted helpers in sequence (mirroring StageA pattern from Phase B1b)
3. Packages telemetry with all RefinementTelemetry fields + stage_type="B" + mode="shell_modifiers"
4. Validates via regression guard test_stage_b_shell_modifiers + engine contract test

## Key Design Decisions
1. **Pattern reuse**: Follow StageA structure exactly (dbex/refinement/stage_a.py, Phase B1b commit 6d1d925)
2. **Lazy imports**: Import helpers INSIDE run() method to avoid circular dependencies
3. **Frozen Stage A params**: Extract from stage_a_telemetry['param_deltas'] and pass to helpers
4. **Telemetry schema completeness**: Include ALL RefinementTelemetry fields (required + optional) to match StageA
5. **param_deltas transform**: Apply softplus transform to shell_modifier_raw for interpretable output
6. **Stage type/mode fields**: Add stage_type="B" and mode="shell_modifiers" per Phase A4 engine protocol

## Do Now Checklist
Ralph will execute 18 steps:
1. Review Phase C1a-loop3 artifacts
2. Create StageB class skeleton (name, configure, run stub)
3. Implement StageB.run() helper orchestration (~200 lines total)
4. Add torch imports (torch, torch.nn.functional)
5. Build Stage A context dict from stage_a_telemetry
6. Call helper1 (_build_stage_b_params) → unpack result
7. Add frozen Stage A params to param_values dict
8. Call helper2 (_build_stage_b_lbfgs_closure) → unpack tuple (compute_loss, closure)
9. Call helper3 (_run_stage_b_lbfgs) → unpack status/metrics
10. Extract telemetry accumulators from telemetry_state (updated in-place)
11. Build param_deltas dict (shell_modifier_raw + shell_modifiers with softplus transform)
12. Package RefinementTelemetry dict (ALL fields + stage_type/mode)
13. Compilation check (python -c "import dbex.refinement.stage_b")
14. Regression guard (test_stage_b_shell_modifiers MUST PASS)
15. Engine contract test (test_engine_executes_mock_stage MUST PASS)
16. Update implementation.md checklist (C1b COMPLETE)
17. Write implementation summary (stage_b_wrapper_implementation.md)
18. Commit and push

## Exit Criteria
- StageB class implements RefinementStage protocol correctly (name, configure, run)
- StageB.run() calls 3 helpers in correct sequence with correct signatures
- Telemetry dict includes all RefinementTelemetry fields + stage_type/mode
- Compilation PASSES (no circular imports)
- Regression guard test_stage_b_shell_modifiers PASSES
- Engine contract test test_engine_executes_mock_stage PASSES
- Implementation summary documents design decisions and test results

## Findings Applied
- **REFINE-008**: Stage B calibrated gate ≥0.002% improvement (helper3)
- **PERF-WARM-009**: Force panel evaluation for initial/final validation (helper2)
- **PERF-WARM-011/012**: CPU fallback logic preserved (helper1)
- **PHYSICS-LOSS-001/002**: Variance-weighted loss + dual metric tracking (helper2)
- **POLICY-001**: Environment Freeze (no new packages)
- **GRADIENT-001**: Autograd graph preservation (helper2 closure)

## Roadmap Alignment
ARCH-REFINE-FLOW-001 Tier 2 — Protocol-based Refinement Engine:
- Phase B COMPLETE (StageA extraction + engine delegation)
- Phase C in progress:
  - C0: Baseline ✓ COMPLETE
  - C1a: Helper extraction (3 loops) ✓ COMPLETE
  - C1b: StageB wrapper (this loop) → ready_for_implementation
  - C2: Engine delegation A→B (next loop if C1b passes)
  - C3-C5: Validation + docs

## Implementation Floor Satisfied
- Production code task: StageB class definition + run() method (~200 lines)
- Validating pytest selectors: test_stage_b_shell_modifiers (regression guard) + test_engine_executes_mock_stage (engine contract)
- Dwell=0 (last loop C1a-loop3 implementation, now ready_for_implementation for C1b wrapper)

## Artifacts
- input.md (comprehensive 18-step Do Now with helper signatures, telemetry schema, pitfalls)
- galph_memory.md (updated with Phase C1b handoff entry + FSM state)
- summary.md (this file)

## Next Loop Expectations
If StageB wrapper PASSES all validations:
- Galph plans Phase C2 (engine delegation A→B sequence)
- Pattern: detect Stage-B-only mode → delegate to RefinementEngine([StageB()]) → return telemetry
- Estimated ~1 loop for C2 implementation

If StageB wrapper BLOCKED:
- Ralph documents blocker in summary.md with 3 hypotheses
- Galph reviews blocker next loop and decides (debug/patch/escalate)
- Common blockers: circular imports, telemetry field mismatch, helper signature error

## Multi-Loop Strategy Validation
Phase C1a-loop1/2/3 (helper extraction) → Phase C1b (wrapper) pattern mirrors Phase B1a-loop1/2/3 → Phase B1b SUCCESS.
Proven incremental progress approach per CLAUDE.md principles.
