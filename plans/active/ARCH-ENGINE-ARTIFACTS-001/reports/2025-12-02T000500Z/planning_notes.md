# ARCH-ENGINE-ARTIFACTS-001 Phase C Planning Notes
## Loop: 2025-12-02T000500Z (Galph planning loop)

## Context
Previous loop (2025-12-05T050000Z) incorrectly reported a blocker due to sigma source infrastructure mismatch.
Reality check (this loop): Both parity tests PASS when run with correct environment variables.

Evidence:
- `test_stage_a_artifact_matches_helper` → PASSED
- `test_stage_b_artifact_matches_helper_shell_mode` → PASSED

The fixture fix from loop 2025-12-02T194000Z successfully resolved the sigma embedding issue.

## Exit Criteria Status

### ✅ Exit Criterion #1: Artifact Channel API
**Status**: SATISFIED

Evidence:
- `RefinementEngine` exposes `engine.artifacts` dict (ARCH-STAGE-CONTEXT-001 Phase B.1)
- Stages populate artifacts via `StageResult` dataclasses
- No private attribute access required
- Documented in docs/spec-db-workflow.md §33

### ✅ Exit Criterion #2: Stage Artifact Parity
**Status**: SATISFIED

Evidence from test run (2025-12-02T000500Z):
```
tests/dbex/test_artifact_parity.py::test_stage_a_artifact_matches_helper PASSED
tests/dbex/test_artifact_parity.py::test_stage_b_artifact_matches_helper_shell_mode PASSED
2 passed, 4 warnings in 46.45s
```

Both tests validate that:
- Stage A: `engine.artifacts["stage_a"].bragg_full` matches `build_final_bragg_from_stage_a_telemetry` output
- Stage B: `engine.artifacts["stage_b"].bragg_full` matches `build_final_bragg_from_stage_b_telemetry` output
- Tolerance: ≤1e-6 relative MSE (PASSED with perfect parity: max_rel=0.000e+00)

### ⏳ Exit Criterion #3: Orchestrator Simplification
**Status**: IN PROGRESS (Phase C required)

Current state analysis:
- dbex/nanobrag_refinement.py:228-241 — Stage A terminal path HAS artifact-first check but keeps fallback
- dbex/nanobrag_refinement.py:369-409 — Stage B terminal path HAS artifact-first check but keeps fallback
- dbex/nanobrag_refinement.py:507-516 — Stage C terminal path ONLY uses artifacts (no fallback, raises RuntimeError if missing)

The code pattern at lines 228-241 and 369-409:
```python
if stage_a_artifacts is not None and hasattr(stage_a_artifacts, 'bragg_full') and stage_a_artifacts.bragg_full is not None:
    bragg_full = stage_a_artifacts.bragg_full
else:
    # Fallback: Build final Bragg using optimized parameters from telemetry
    from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry
    bragg_full = build_final_bragg_from_stage_a_telemetry(...)
```

**Problem**: Exit Criterion #3 requires "no longer calling _build_final_bragg_from_stage_b_telemetry" but these fallback branches still exist and call the helpers.

**Why fallbacks exist**: Defensive coding for backward compatibility with "older binaries that don't populate artifact bragg_full" (per line 232 comment).

**Why fallbacks can be removed now**:
1. Parity tests prove artifacts ARE populated correctly (Exit Criterion #2 satisfied)
2. Stage wrappers unconditionally emit artifacts (verified by code inspection in Phase A.3)
3. Stage C already requires artifacts (line 513-516 raises RuntimeError if missing)
4. No evidence of "older binaries" — all code paths go through RefinementEngine

## Phase C Scope

### C1: Simplify orchestrator to artifact-only path

**Target files**: `dbex/nanobrag_refinement.py`

**Changes required**:

1. **Stage A terminal path (lines 228-241)**:
   - Remove `else` fallback branch
   - Replace with RuntimeError if artifact missing (matching Stage C pattern)
   - Simplify to: `bragg_full = stage_a_artifacts.bragg_full`

2. **Stage B terminal path (lines 369-409)**:
   - Remove `else` fallback branch (41 lines of fallback logic)
   - Replace with RuntimeError if artifact missing
   - Simplify to: `bragg_full = stage_b_artifacts.bragg_full`

3. **Delete obsolete comments** about "older binaries" and fallback logic

**Validation**:
- Rerun both parity tests (should still PASS)
- Rerun Stage A/B/C smoke tests to ensure no regressions
- Confirm RuntimeError paths are never hit (artifacts always populated)

### C2: Remove reconstruction helper imports (optional cleanup)

**Rationale**: If run_nanobrag_refinement no longer calls the helpers directly, their imports can be removed from this module.

**Note**: The helpers should remain in `dbex/refinement/reconstruction.py` because:
- They may be used by other tools/tests
- Parity tests still need them as reference implementations
- Other consumers might import them directly

**Action**: Remove these imports from dbex/nanobrag_refinement.py:
- Line 233: `from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry`
- Line 374: `from dbex.refinement.reconstruction import build_final_bragg_from_stage_b_telemetry`

### C3: Documentation updates

**Files to update**:
1. `docs/architecture/live_backend.md` — Update to reflect artifact-only flow
2. `docs/architecture/module_map.md` — Update run_nanobrag_refinement entry
3. `plans/active/ARCH-ENGINE-ARTIFACTS-001/implementation.md` — Mark Phase C checklist items complete

## Risks & Mitigations

### Risk: Breaking tools that depend on fallback behavior
**Likelihood**: Low
**Mitigation**: All code paths use RefinementEngine which populates artifacts. If a tool bypasses the engine, it's already broken.

### Risk: Edge cases where artifacts aren't populated
**Likelihood**: Very low
**Evidence**: Parity tests prove artifacts ARE populated for Stage A/B terminal modes. Stage C already requires artifacts.
**Mitigation**: RuntimeError will catch any such cases immediately rather than silently using stale/incorrect fallback data.

### Risk: HDF5 output changes
**Likelihood**: None
**Mitigation**: The artifact values are identical to fallback helper outputs (proven by parity tests). Removing the unused fallback code path won't change observable behavior.

## Implementation Strategy

**Mode**: Implementation (not planning-only)
**Action Type**: Refactoring (removing dead code)
**Initiative Type**: architecture (per fix_plan.md)

**Do Now** for Ralph:
1. Edit `dbex/nanobrag_refinement.py`:
   - Stage A terminal: Remove lines 230-241 (fallback), replace with direct artifact access + error check
   - Stage B terminal: Remove lines 371-409 (fallback), replace with direct artifact access + error check
2. Run parity tests: `pytest -vv tests/dbex/test_artifact_parity.py`
3. Run Stage A/B smoke tests to ensure no regressions
4. Capture test results and updated code in reports

**Mapped Tests**:
- `tests/dbex/test_artifact_parity.py::test_stage_a_artifact_matches_helper`
- `tests/dbex/test_artifact_parity.py::test_stage_b_artifact_matches_helper_shell_mode`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_baseline_smoke`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`

## Success Criteria
- All parity tests PASS (2/2)
- All smoke tests PASS (4/4 mapped)
- Code size reduction: ~50 lines removed (fallback logic)
- Complexity reduction: Simpler artifact-only path, no defensive branching
- Documentation updated to reflect simplified architecture

## Artifacts for Next Loop
- Edited `dbex/nanobrag_refinement.py` (diff showing removed fallback logic)
- Test logs proving all validations pass
- Updated implementation.md with Phase C completion notes
