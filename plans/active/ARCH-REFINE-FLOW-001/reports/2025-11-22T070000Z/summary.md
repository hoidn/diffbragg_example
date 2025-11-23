### Turn Summary
Authored comprehensive Phase C1a-loop3 Do Now directing final multi-loop extraction step: extract `_run_stage_b_lbfgs` helper (~100 lines LBFGS execution + improvement gate), fix helper2 signature bug (return tuple `(compute_loss, closure)` not just `closure`), wire all 3 helpers into run_nanobrag_refinement (~610 lines → ~50 lines orchestration), MANDATORY regression guard test_stage_b_shell_modifiers.
Identified and documented helper2 signature blocker (helper3 needs BOTH functions for final validation, current signature returns only closure).
Resolution: update helper2 line 2586 to return tuple matching Phase B1a-loop2 Stage A pattern.
Next loop: Ralph executes C1a-loop3 implementation (extract, fix, wire, regression guard MUST PASS).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/ (input.md with 10-step protocol)

---

# Phase C1a-loop3 Planning Summary

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C1a-loop3 planning handoff)

## Action Type
ready_for_implementation

## Objective
Plan final multi-loop extraction step for Stage B: extract helper3, fix helper2 signature bug, wire all 3 helpers, run regression guard.

## Key Decisions

### 1. Multi-Loop Extraction Complete (3 loops)
Phase C1a extraction follows proven Phase B1a pattern:
- **C1a-loop1** (COMPLETE 2025-11-22T060833Z): Extract `_build_stage_b_params` helper (~184 lines)
- **C1a-loop2** (COMPLETE 2025-11-22T063000Z): Extract `_build_stage_b_lbfgs_closure` helper (~317 lines, TWO nested functions)
- **C1a-loop3** (IN PROGRESS 2025-11-22T070000Z): Extract `_run_stage_b_lbfgs` helper (~100 lines) + fix helper2 signature + wire all 3 helpers + MANDATORY regression guard

### 2. Helper2 Signature Blocker Identified

**Current state**: `_build_stage_b_lbfgs_closure` returns ONLY `closure_stage_b` (line 2586).

**Problem**: Helper3 `_run_stage_b_lbfgs` needs BOTH `compute_loss_stage_b` AND `closure_stage_b` for final validation (force_panel_eval checks).

**Resolution**: Update helper2 signature to return tuple `(compute_loss_stage_b, closure_stage_b)` matching Phase B1a-loop2 Stage A pattern.

**Fix location**: Line 2586 in `_build_stage_b_lbfgs_closure`
```python
# Change from:
return closure_stage_b

# To:
return compute_loss_stage_b, closure_stage_b
```

### 3. Helper3 Extraction Scope

**Lines to extract**: 3427-3490 (~64 lines of LBFGS execution logic)

**Components**:
- Initial full validation (lines 3431-3444)
- LBFGS optimizer.step() call (line 3447)
- Exception handler (lines 3449-3451)
- Final validation + best snapshot restore (lines 3453-3473)
- Final metrics assembly (lines 3475-3479)
- Improvement gate check (lines 3481-3490)

**Total helper size**: ~100 lines (including signature, param extraction, return dict)

### 4. Wiring Strategy

**Replace**: Lines ~3040-3540 (~610 lines inline Stage B code)

**With**: ~50 lines orchestration:
1. Call `_build_stage_b_params` (helper1)
2. Unpack param_values and context dicts
3. Add frozen Stage A tensors to param_values (8 tensors + best_loss_full)
4. Call `_build_stage_b_lbfgs_closure` (helper2) → unpacks to `(compute_loss_stage_b, closure_stage_b)`
5. Call `_run_stage_b_lbfgs` (helper3)
6. Extract shell_modifier_raw from param_values
7. Keep existing final Bragg generation AS-IS (lines 3492-3600)

### 5. Regression Guard MANDATORY

**Test**: `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -v`

**Environment**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
DBEX_SMOKE_SIGMA_SOURCE=cli_override
DBEX_SMOKE_DETECTOR_SIZE=small
KMP_DUPLICATE_LIB_OK=TRUE
NANOBRAGG_DISABLE_COMPILE=1
```

**Acceptance**: MUST PASS (exit code 0). If FAIL → revert changes, document blocker, escalate to Galph.

### 6. Telemetry Comparison

**Baseline**: Phase C0 (2025-11-23T061726Z) telemetry_small.json

**Expected metrics**:
- Initial chi²: ~660M (small detector, Stage A final loss)
- Stage B improvement: typically 0.001-0.01% (below REFINE-008 gate, expect early_stop)
- Status: "early_stop" or "ok"

**Validation**:
- Status matches baseline
- Telemetry structure complete
- No regressions in chi² or MSE traces

## Implementation Floor Satisfied

**Production code tasks**:
1. Extract `_run_stage_b_lbfgs` helper (~100 lines)
2. Fix `_build_stage_b_lbfgs_closure` signature (return tuple)
3. Wire all 3 helpers into `run_nanobrag_refinement` Stage B branch

**Validating pytest selector**: test_stage_b_shell_modifiers (MANDATORY regression guard)

**Telemetry comparison protocol**: Compare with Phase C0 baseline metrics

## Critical Pitfalls Documented

1. **Helper2 signature bug**: MUST fix to return tuple, not scalar
2. **Frozen tensor injection**: MUST add all 8 Stage A tensors + best_loss_full to param_values
3. **param_values dict consistency**: Ensure all keys helper2/helper3 expect are populated by helper1
4. **Final step calculation**: Access `loss_trace_sample_b` from param_values, not local scope
5. **Trace mutation bug**: Best metric tuples are `(value, step)` not `[value, step]`
6. **Device routing**: Preserve CPU fallback logic (PERF-WARM-011/012)
7. **Best snapshot restore**: Always restore AFTER final validation
8. **Improvement gate**: Check `best_loss_full[0] > 0` before computing improvement_b
9. **Regression guard MANDATORY**: Revert if FAIL, do NOT commit broken code
10. **NO early optimization**: Pure extraction + wiring, preserve exact logic

## Findings Applied

- **REFINE-008**: Stage B ≥0.002% improvement gate (helper3 must check)
- **PERF-WARM-009**: Force panel evaluation for initial/final validations
- **PERF-WARM-011**: CPU fallback for Stage B panel-mode runs
- **PERF-WARM-012**: Clone Stage A context to CPU when fallback active
- **PHYSICS-LOSS-001**: Dual metric tracking (chi_squared + masked_mse)
- **PHYSICS-LOSS-002**: Variance floor statistics
- **POLICY-001**: Environment Freeze (no new imports except helper2 fix)
- **Phase B precedent**: B1a-loop3 SUCCESS (commit caa510e, bugfix + regression guard PASSED)

## Phase C1a Progress

| Loop | Objective | Status | Lines | Artifacts |
|------|-----------|--------|-------|-----------|
| C1a-loop1 | Extract `_build_stage_b_params` | ✓ COMPLETE | ~184 | 2025-11-22T060833Z |
| C1a-loop2 | Extract `_build_stage_b_lbfgs_closure` | ✓ COMPLETE | ~317 | 2025-11-22T063000Z |
| C1a-loop3 | Extract `_run_stage_b_lbfgs` + wire + regression | IN PROGRESS | ~100 + wiring | 2025-11-22T070000Z |

**Total line reduction expected**: ~610 lines inline code → ~50 lines orchestration (~560 line reduction)

## Next Steps

### If C1a-loop3 Succeeds (regression guard PASSES)
1. Mark Phase C1a COMPLETE in implementation.md
2. Next loop: Galph plans Phase C1b (StageB wrapper class)
3. StageB.run() calls 3 extracted helpers directly
4. Package telemetry with RefinementTelemetry fields + stage_type="B"
5. Regression guard + engine contract test

### If C1a-loop3 Blocked
1. Ralph documents blocker in phase_c1a_loop3_blocker.md
2. Record error signature, attempted fixes
3. Revert changes: `git checkout dbex/nanobrag_refinement.py`
4. Galph reviews blocker and decides:
   - Debug/patch specific issue
   - Simplify wiring scope
   - Escalate to multi-loop if complexity too high

## Dwell Enforcement
- **Last loop**: C1a-loop2 (ready_for_implementation, helper2 extraction)
- **This loop**: ready_for_implementation (planning Phase C1a-loop3)
- **Dwell count**: 0 (reset after C1a-loop2 completion)
- **State**: ready_for_implementation
- **Implementation floor**: Satisfied (production code tasks + regression guard)

## Roadmap Alignment
- **Tier**: 2 (Architectural Maturity)
- **Initiative**: ARCH-REFINE-FLOW-001
- **Phase**: C1a-loop3 (final multi-loop extraction step)
- **Dependencies**: C1a-loop1 ✓, C1a-loop2 ✓
- **Blockers**: None (helper2 signature fix documented in Do Now)

## Confidence Assessment
- **Helper extraction scope**: HIGH (~95%) — mirrors B1a-loop3 pattern, well-bounded
- **Helper2 signature fix**: HIGH (~95%) — one-line change, matches Phase B precedent
- **Wiring complexity**: MEDIUM (~75%) — requires careful frozen tensor injection, param_values dict consistency
- **Regression guard**: HIGH (~90%) — test exists, Phase C0 baseline captured, metrics well-understood

## Artifacts

### Input.md (Phase C1a-loop3 Do Now)
- **Summary**: Extract helper3, fix helper2, wire helpers, regression guard
- **Mode**: none
- **Mapped tests**: test_stage_b_shell_modifiers (MANDATORY regression guard)
- **Artifacts**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/
- **10-step protocol**: Extract → Fix → Wire → Compile → Regression → Telemetry → Update → Summary → Commit

### Galph Memory Entry
- **Focus**: ARCH-REFINE-FLOW-001 Phase C1a-loop3
- **Action Type**: ready_for_implementation
- **State**: ready_for_implementation
- **Dwell**: 0
- **Next Actions**: Ralph executes C1a-loop3, regression guard MUST PASS

### Fix Plan Update
- **C1a-loop2**: Marked COMPLETE with helper2 signature blocker note
- **C1a-loop3**: Marked IN PROGRESS with extraction scope, signature fix, wiring details

## Lessons from Phase B1a

### Success Patterns
1. **Multi-loop extraction** reduces risk and token pressure
2. **Compilation-only loops** (C1a-loop1, C1a-loop2) enable incremental progress
3. **param_values dict pattern** provides clean helper interfaces
4. **Frozen tensor injection** separates mutable/immutable state
5. **Turn Summary requirement** improves communication

### Pitfalls Avoided
1. **Single-loop extraction** of all 3 helpers (too complex, reversion risk)
2. **Signature mismatches** between helpers (helper2 bug caught in planning)
3. **Missing dict keys** causing NameError (Phase B1a-loop3 bug learned)
4. **Tuple vs list confusion** for best metric tracking
5. **Early optimization** during extraction (pure extraction + wiring only)

## Phase C Multi-Loop Strategy
- **Total estimate**: 6-7 loops
- **C0**: Baseline artifacts (COMPLETE 2025-11-23T061726Z)
- **C1a**: Helper extraction (3 sub-loops, C1a-loop3 IN PROGRESS)
- **C1b**: StageB wrapper class (next after C1a-loop3)
- **C2**: Engine delegation (A→B sequence)
- **C3**: Full validation suite (small + full detectors, DB-AT selectors)

**Status**: On track per Phase B precedent. Phase B took 7 loops total, Phase C estimated 6-7 loops.
