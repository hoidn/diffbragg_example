# Phase B2 Planning Summary — Engine Delegation for Stage-A-Only Mode

**Loop:** i=196 (Galph planning)
**Date:** 2025-11-23T050432Z
**Initiative:** ARCH-REFINE-FLOW-001 Phase B2 — Engine Delegation
**Mode:** Planning (ready_for_implementation handoff)

## Context

Phase B1b is COMPLETE (commit 6d1d925, 2025-11-23T045012Z):
- StageA.run() now calls three extracted helpers directly (no recursion risk)
- Telemetry packaging includes all RefinementTelemetry fields + stage_type/mode per Phase A4 schema
- Compilation PASSED, regression guard test_stage_a_expansion PASSED (12.40s)
- Engine contract test test_engine_executes_mock_stage PASSED

## Problem Statement

**SPEC:** docs/spec-db-workflow.md §7 — Refinement Protocol Architecture requires:
> "The internal Python API (RefinementEngine or equivalent) SHALL accept an ordered list of Stage objects and MUST NOT hardcode the Stage A→B→C flow."

Currently, `run_nanobrag_refinement` executes all stages inline via extracted helpers. Phase B2 introduces **conditional engine delegation** for Stage-A-only mode while keeping Stage B/C inline until Phases C/D.

## Phase B2 Objective

Update `run_nanobrag_refinement` to:
1. **Detect Stage-A-only mode:** `enable_stage_c=False AND enable_stage_b=False`
2. **Delegate to RefinementEngine:** Instantiate `RefinementEngine([StageA()])` and call `engine.run()`
3. **Keep Stage B/C inline:** Preserve existing inline logic when either Stage B or C is enabled
4. **Preserve behavior:** Regression guard test_stage_a_expansion must pass unchanged

## Implementation Scope

### Stage Detection Logic

Add mode detection at the start of `run_nanobrag_refinement` (after config instantiation):

```python
# Detect Stage-A-only mode for engine delegation
stage_a_only_mode = (not config.enable_stage_c and not config.enable_stage_b)

if stage_a_only_mode:
    # === ENGINE DELEGATION PATH (Phase B2) ===
    # Instantiate RefinementEngine with StageA
    from dbex.refinement.engine import RefinementEngine
    from dbex.refinement.stage_a import StageA

    # Build inputs dict per StageA.run() contract
    engine_inputs = {
        'refinement_inputs': inputs,
        'detector': detector,
        'beam': beam,
        'crystal': crystal,
        'hkl_grid': hkl_grid,
        'hkl_metadata': hkl_metadata,
        'baseline_crystal': baseline_crystal,
        'baseline_detector': baseline_detector,
    }

    # Create engine with StageA
    engine = RefinementEngine(stages=[StageA()], config=config)

    # Execute engine and get telemetry
    telemetry_dict = engine.run(engine_inputs)

    # Extract StageA telemetry (keyed by stage.name = "stage_a")
    telemetry_a = telemetry_dict["stage_a"]

    # Build final bragg array using optimized parameters from telemetry
    # (same logic as current inline path, lines 2046-2285)
    bragg_full = _build_final_bragg_from_stage_a_telemetry(
        telemetry_a, detector, beam, crystal, inputs, hkl_grid,
        hkl_metadata, config, device, dtype
    )

    # Return with telemetry dict using "A" key for backward compatibility
    return bragg_full, {"A": telemetry_a}

else:
    # === INLINE PATH (existing implementation) ===
    # Keep current Stage A/B/C inline logic unchanged
    # (lines 1950-3407)
    ...existing code...
```

### Helper: _build_final_bragg_from_stage_a_telemetry

Extract the final Bragg reconstruction logic (lines 2046-2285) into a helper that:
- Accepts telemetry dict with optimized parameters
- Unpacks param_deltas, converts to torch tensors
- Loops over panels to regenerate Bragg array with final geometry
- Returns `bragg_full` (np.ndarray, shape=[n_panels, slow, fast])

**Key Requirements:**
1. **No behavior change:** Final Bragg array must be identical to inline path
2. **Telemetry compatibility:** Engine returns RefinementTelemetry instance; extract fields as dict
3. **Lazy imports:** Import engine/StageA inside the `if stage_a_only_mode:` block to avoid circular imports
4. **Device/dtype neutrality:** All tensors use config.device/dtype

### Validation Protocol

1. **Regression guard (primary):** `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
   - Environment: `DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
   - Expected: 1 passed, test should use engine delegation path
   - Validate telemetry structure matches inline path

2. **Engine contract:** `pytest -vv tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage`
   - Confirms engine protocol remains stable

3. **Compilation check:** `python -c "from dbex import nanobrag_refinement; print('OK')"`
   - Validates no import errors

## Implementation Steps (10 tasks for Ralph)

1. **Review Phase B1b artifacts** (plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/)
   - Confirm StageA.run() implementation
   - Review telemetry schema

2. **Extract _build_final_bragg_from_stage_a_telemetry helper** (~240 lines)
   - Copy lines 2046-2285 from run_nanobrag_refinement
   - Accept telemetry dict + all required inputs
   - Return bragg_full array
   - Place helper at ~line 1888 (after _run_stage_a_lbfgs)

3. **Add stage detection logic** (after line 1951 `if config is None:`)
   - Compute `stage_a_only_mode = (not config.enable_stage_c and not config.enable_stage_b)`

4. **Implement engine delegation branch** (~50 lines)
   - Lazy import RefinementEngine, StageA
   - Build engine_inputs dict
   - Instantiate engine with [StageA()]
   - Call engine.run(engine_inputs)
   - Extract telemetry_dict["stage_a"]
   - Call _build_final_bragg_from_stage_a_telemetry
   - Return (bragg_full, {"A": telemetry_a})

5. **Wrap existing inline code in else branch**
   - Move lines 1953-3407 into `else:` block (inline path)
   - Preserve all existing logic unchanged

6. **Compilation check**
   - Run: `python -c "from dbex import nanobrag_refinement; print('OK')"`
   - Expected: OK (exit code 0)

7. **Regression guard test**
   - Run: `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
   - Environment: `DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
   - Expected: 1 passed (test calls engine delegation path)
   - Archive log: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/pytest_stage_a_expansion.log

8. **Engine contract validation**
   - Run: `pytest -vv tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage`
   - Expected: 1 passed
   - Archive log: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/pytest_engine.log

9. **Update implementation.md checklist**
   - Mark B2 as complete with commit hash and timestamp
   - Update B3 status (next pending task)

10. **Write implementation summary + commit**
    - Create phase_b2_implementation_summary.md
    - Write Turn Summary block to summary.md
    - Commit: "ARCH-REFINE-FLOW-001 Phase B2: Engine delegation for Stage-A-only mode — tests: passed"
    - Push

## Key Design Decisions

1. **Conditional delegation (not wholesale replacement):** Only Stage-A-only mode uses the engine; Stage B/C combinations stay inline until Phases C/D extract them. This minimizes risk and preserves existing test coverage.

2. **Telemetry key mapping:** Engine returns `{"stage_a": RefinementTelemetry(...)}`, but legacy code expects `{"A": ...}`. Map "stage_a" → "A" for backward compatibility.

3. **Final Bragg reconstruction helper:** Extract lines 2046-2285 to avoid duplication; both engine path and inline path will call this helper once telemetry is available.

4. **Lazy imports:** Import RefinementEngine/StageA inside the delegation branch to avoid circular import at module load time (dbex.nanobrag_refinement is heavy; dbex.refinement modules are light).

5. **No telemetry schema changes:** StageA.run() already returns a dict matching RefinementTelemetry structure; engine converts it to RefinementTelemetry instance, we extract it back to dict for backward compatibility.

## Expected Outcomes

### Path A: All Tests PASS (expected)
- Engine delegation path executes successfully
- Regression guard test_stage_a_expansion PASSED
- Telemetry structure matches inline path
- bragg_full array matches inline path (numerically identical)
- **Next loop (i=197):** Galph plans Phase B3 (full smoke + DB-AT validation)

### Path B: Regression Guard Failure
- Test expects specific telemetry structure that engine path breaks
- Telemetry key mismatch ("stage_a" vs "A")
- **Action:** Ralph documents failure signature → Galph reviews → fix telemetry mapping

### Path C: Bragg Array Mismatch
- Final Bragg reconstruction helper produces different output
- Parameter unpacking from telemetry incorrect
- **Action:** Ralph compares inline vs engine path Bragg arrays → Galph reviews → debug helper

### Path D: Import/Compilation Error
- Circular import when importing RefinementEngine/StageA
- Missing imports in helper function
- **Action:** Ralph documents error → Galph reviews → fix imports

## Artifacts

- **Root:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/`
- **Files (to be created by Ralph):**
  - `pytest_stage_a_expansion.log` (regression guard)
  - `pytest_engine.log` (engine contract validation)
  - `phase_b2_implementation_summary.md` (deliverables summary)
  - `summary.md` (Turn Summary block)

## Commit Message Template

```
ARCH-REFINE-FLOW-001 Phase B2: Engine delegation for Stage-A-only mode — tests: passed

- Added stage detection logic (enable_stage_c=False AND enable_stage_b=False)
- Implemented engine delegation path with RefinementEngine([StageA()])
- Extracted _build_final_bragg_from_stage_a_telemetry helper (~240 lines)
- Wrapped existing inline logic in else branch (Stage B/C combinations)
- Regression guard test_stage_a_expansion PASSED (engine path active)
- Phase B2 COMPLETE, ready for Phase B3 full smoke validation
```

## Next Actions

**Ralph (i=196):** Execute Phase B2 implementation per input.md Do Now (10 steps)

**Galph (i=197):** If B2 PASSES → Plan Phase B3:
- Run Stage A smoke on full detector (DBEX_SMOKE_DETECTOR_SIZE=full)
- Capture telemetry JSON + pytest logs
- Run DB-AT-010 (Gradcheck) and DB-AT-024 (Mapping) selectors
- Verify parity thresholds and gates remain satisfied

If B2 BLOCKED → Review Ralph's blocker report and decide escalation path.

## Findings Applied

- **PHYSICS-LOSS-001/002/003**: StageA telemetry includes all required fields (chi_squared, masked_mse, variance_floor, canonical metadata)
- **PERF-WARM-001**: StageA wrapper preserves warm-cache telemetry contract (perf_counters, cache_mode, roi_mode)
- **GEOMETRY-003/004**: Baseline misset derivation and incremental UB parameterization handled inside StageA.run()
- **GRADIENT-001**: Parameter extraction from telemetry must preserve autograd (though final Bragg is no_grad)
- **CONVERGENCE-001**: Zero-delta bypass handled inside helper2 (transparent to engine delegation)

## Spec Alignment

- **spec-db-workflow.md:33**: RefinementEngine accepts ordered Stage list (✓ Phase B2 uses engine for Stage-A-only)
- **spec-db-workflow.md:36**: Engine does NOT hardcode A→B→C (✓ Phase B2 conditional on config flags)
- **spec-db-tracing.md §2**: Telemetry aggregation keyed by stage.name (✓ "stage_a" → "A" mapping)
- **dbex/refinement/stage.py:23-84**: RefinementStage protocol (✓ StageA implements all methods)
- **dbex/refinement/engine.py:21-125**: RefinementEngine contract (✓ Phase B2 uses engine.run())

## Roadmap Alignment

- **Tier:** 2 (Architectural Maturity)
- **Initiative:** ARCH-REFINE-FLOW-001 (Protocol-based Refinement Engine)
- **Milestone:** Phase B2 (engine delegation for Stage-A-only mode)
- **Strategy:** Incremental engine adoption (A-only first, then A+B, then A+B+C)
- **Next:** Phase B3 (full smoke + DB-AT validation) if B2 PASSES

## Risks & Mitigations

1. **Risk:** Telemetry structure mismatch breaks downstream code
   - **Mitigation:** Map "stage_a" → "A" for backward compatibility

2. **Risk:** Final Bragg reconstruction differs from inline path
   - **Mitigation:** Extract identical logic into shared helper

3. **Risk:** Circular imports when loading engine/StageA
   - **Mitigation:** Lazy imports inside delegation branch

4. **Risk:** Test coverage gaps for engine path
   - **Mitigation:** Phase B3 includes full smoke + DB-AT selectors

5. **Risk:** Stage B/C combinations break when wrapped in else
   - **Mitigation:** No code changes in else branch; existing tests continue to pass
