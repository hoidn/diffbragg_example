# ARCH-REFACTOR-001 Phase 0 Planning Analysis

**Date:** 2025-11-24T070000Z
**Loop:** Galph planning (i=252 supervisor turn)
**Focus:** ARCH-REFACTOR-001 Phase 0 — Test Discipline Baseline
**State:** planning
**Dwell:** 0 (first planning loop for this focus)

## Context

**Prior Focus:** PERF-WARM-SIM-001 Phase D (loops i=250-252)
- **Last Ralph loop (i=252):** Implemented chi² fix (commit 27070a9), validation BLOCKED by ENV-CUDA-001
- **Blocker Nature:** Environmental CUDA caching allocator error in Stage A ("These storage data ptrs not allocated in pool")
- **Ralph's Analysis:** Error occurs BEFORE fix code executes (temporal impossibility), addresses change between runs, zero LBFGS iterations
- **Environment Freeze Decision:** Per CLAUDE.md and galph_prompt, cannot diagnose/fix environmental issues (PERF-WARM-SIM-001 is NOT "environment maintenance" focus)
- **Pivot Rationale:** PERF-WARM-SIM-001 blocked by environmental issue outside our control, mark blocked with return condition (env resolution OR retry on different session/hardware)

**New Focus Selection:** ARCH-REFACTOR-001 per Execution Roadmap Tier 3 priority
- **Status Change:** pending → in_progress (was blocked by TORCH-GEOMETRY-CONVERGENCE-001, now DONE 2025-11-22T244500Z)
- **Unblock Rationale:** TORCH-GEOMETRY-CONVERGENCE-001 Phase C6b complete (chi² drift +0.0083%, CC≈1.0, CONVERGENCE-001 finding documented)
- **Priority:** Tier 3 Architectural Maturity (Refactoring), foundational for TORCH-REFINE-004 and other Tier 3 work

## Phase 0 Objectives

**Goal:** Prove test-writing discipline exists BEFORE refactoring. Tests written against CURRENT code provide safety net for migration.

**Checklist (from implementation.md:80-89):**
- 0.1: Unit test `derive_u_matrix` in CURRENT location (`dbex/nanobrag_bridge.py`) — `test_derive_u_matrix_roundtrip` validates MOSFLM A* → (U, B_ideal) → A* reconstruction within 1e-6
- 0.2: Unit test `variance_weighted_loss` in CURRENT location — `test_variance_weighted_loss_sigma_floor` validates sigma_floor clamping per PHYSICS-LOSS-001
- 0.3: Achieve 80% coverage of core math — pytest --cov coverage check
- 0.4: Regression guard — Run test_stage_a_expansion + DB-AT-024 to establish baseline

**Rationale (implementation.md:86-89):**
- Validates team CAN write tests (if tests never materialize, refactoring is pointless - same discipline problem persists)
- Tests written against CURRENT code become parity validators during migration (run old tests against new modules)
- **Gate:** Phase 0 must complete with ≥80% coverage BEFORE proceeding to Phase A physics extraction

## Scope Analysis

### 0.1: Test derive_u_matrix_roundtrip

**Target Function:** `dbex/nanobrag_bridge.py::derive_u_matrix_from_mosflm_a_star`
- **Signature:** `derive_u_matrix_from_mosflm_a_star(a_star: np.ndarray) -> Tuple[np.ndarray, np.ndarray]` (returns U, B_ideal)
- **Spec Reference:** docs/config_crosswalk.md §Crystal Geometry Mapping (MOSFLM A* = U @ B_ideal)
- **Finding Reference:** GEOMETRY-003 (baseline misset derivation, B_ideal convention)
- **Test Strategy:**
  1. Create synthetic A* matrix from known U (orthogonal) and B_ideal (upper triangular)
  2. Call derive_u_matrix_from_mosflm_a_star(A*)
  3. Assert reconstructed U within 1e-6 of input U (orthogonality, det(U)=1)
  4. Assert reconstructed B_ideal within 1e-6 of input B_ideal
  5. Assert A* reconstruction: U_derived @ B_ideal_derived ≈ A* within 1e-6
- **Edge Cases:** Handle det(U) sign ambiguity, near-zero cell params (small B_ideal values)
- **Estimated Lines:** ~40 lines (setup synthetic matrices ~10, 3 assertions ~20, edge case tests ~10)

### 0.2: Test variance_weighted_loss_sigma_floor

**Target Function:** `dbex/nanobrag_refinement.py::_compute_variance_weighted_loss` (or equivalent in nanobrag_bridge.py)
- **Signature:** `_compute_variance_weighted_loss(target, model, mask, sigma_readout, variance_floor, ...) -> torch.Tensor`
- **Spec Reference:** docs/spec-db-core.md §Variance Definition (V = I_model + sigma² (detached), clamp floor)
- **Finding Reference:** PHYSICS-LOSS-001 (variance-weighted loss + metadata manifest), PHYSICS-LOSS-003 (chi² consistency)
- **Test Strategy:**
  1. Create synthetic target/model tensors with known pixel values
  2. Call _compute_variance_weighted_loss with sigma_readout=1.0, variance_floor=2.0
  3. Assert variance clamping: V = max(model + 1.0, 2.0) per spec
  4. Assert loss calculation: sum((target - model)² / V * mask) / sum(mask)
  5. Test edge cases: zero mask (division safety), negative model (should clamp), zero variance_floor
- **Edge Cases:** Zero mask coverage (should return 0 or NaN with safe handling), large outliers (no overflow)
- **Estimated Lines:** ~60 lines (setup tensors ~15, 4 test cases ~35, edge cases ~10)

### 0.3: Coverage Gate

**Coverage Command:**
```bash
pytest --cov=dbex.nanobrag_bridge --cov=dbex.nanobrag_refinement \
  --cov-report=term --cov-report=html:plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/coverage_phase0 \
  tests/dbex/test_geometry_current.py tests/dbex/test_physics_loss_current.py
```

**Target Functions for 80% Coverage:**
- `derive_u_matrix_from_mosflm_a_star` (nanobrag_bridge.py)
- `recover_cell_from_a_star` (nanobrag_bridge.py, if exists)
- `compute_baseline_misset` (nanobrag_bridge.py)
- `matrix_to_quaternion` (nanobrag_bridge.py)
- `_compute_variance_weighted_loss` (nanobrag_refinement.py)
- `compute_masked_mse_loss` (nanobrag_refinement.py, if exists)

**Coverage Success Criteria:** ≥80% line coverage for target functions (measured per-function, not module-wide)

### 0.4: Regression Baseline

**Selectors:**
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (Stage A smoke test, ~12s runtime)
- `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` (mapping parity, ~32s runtime)

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke \
  > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/regression_baseline.log 2>&1
```

**Success Criteria:** Both tests PASS (no skips, no failures), establish baseline metrics (runtime, chi², correlation) for Phase A validation

## Implementation Strategy

**TDD Workflow:**
1. **Write minimal failing tests first** (test_geometry_current.py, test_physics_loss_current.py) with xfail markers
2. **Run tests to confirm failure** (RED phase)
3. **Verify CURRENT code satisfies tests** (tests should PASS against nanobrag_bridge.py/nanobrag_refinement.py WITHOUT modifications)
4. **Achieve 80% coverage gate** via coverage report
5. **Run regression baseline** to establish metrics before Phase A refactoring

**Test File Locations:**
- `tests/dbex/test_geometry_current.py` (NEW file, ~60 lines including 0.1 test + helper fixtures)
- `tests/dbex/test_physics_loss_current.py` (NEW file, ~80 lines including 0.2 test + synthetic fixtures)

**Artifacts:**
- `pytest_geometry_current.log` (0.1 test run)
- `pytest_physics_loss_current.log` (0.2 test run)
- `coverage_phase0/` (HTML coverage report)
- `regression_baseline.log` (0.4 smoke tests)
- `phase_0_decision.md` (gate assessment: PASS/FAIL for ≥80% coverage)

## Risks & Mitigations

**R1: Target functions don't exist or are named differently**
- **Mitigation:** Grep codebase for "derive_u_matrix", "_compute_variance_weighted_loss" to locate actual function names; update test imports accordingly
- **Fallback:** If functions are inline/nested, extract them to module level FIRST (minimal refactoring to enable testing), then write tests

**R2: Coverage <80% due to untestable branches (error handling, device/dtype paths)**
- **Mitigation:** Focus on "happy path" coverage for core math (orthogonal U, positive variance); defer edge cases to Phase A if needed
- **Acceptance:** 80% is per-function line coverage, NOT branch coverage; skip unreachable branches (e.g., CUDA-only paths when testing on CPU)

**R3: Regression tests fail due to ENV-CUDA-001 carryover**
- **Mitigation:** Use NANOBRAGG_DISABLE_COMPILE=1 + small detector fixture (same env as PERF-WARM-SIM-001 evidence loops)
- **Fallback:** If CUDA error persists, mark regression baseline BLOCKED (same as PERF-WARM-SIM-001), continue Phase 0 tests on CPU-only path, defer full validation to env resolution

**R4: Tests pass but don't provide safety net (too shallow)**
- **Mitigation:** Assertions must validate numerical correctness (1e-6 tolerances, reconstruction roundtrips, spec-compliant variance clamping), not just "doesn't crash"
- **Review:** Phase 0 gate includes manual review of test quality before proceeding to Phase A

## Estimated Effort

**Checklist Items:**
- 0.1: Test derive_u_matrix — 1 hour (grep locate function ~10min, write test ~30min, run/validate ~20min)
- 0.2: Test variance_weighted_loss — 1.5 hours (locate function ~15min, write test + synthetic fixtures ~60min, run/validate ~15min)
- 0.3: Coverage gate — 30 min (run coverage ~10min, analyze report ~10min, adjust tests if <80% ~10min)
- 0.4: Regression baseline — 30 min (run 2 tests ~45s, archive logs ~5min, extract metrics ~20min)

**Total Phase 0 Estimate:** ~3.5 hours (single loop feasible with focused scope)

**Loop Allocation:**
- **Next loop (i=253):** Ralph implementation (0.1 + 0.2 + 0.3 + 0.4 checklist execution)
- **Decision synthesis:** PASS (≥80% coverage, regression baseline established) → Phase A planning; FAIL (coverage <80%) → adjust tests, retry

## Decision Tree

**Path A (Phase 0 PASS — Coverage ≥80%, Regression Baseline Established):**
- **Next Actions:** Galph Phase A planning (physics extraction scope, A1-A4 checklist, migration strategy)
- **Expected Artifacts:** coverage_phase0/ report, regression_baseline.log with metrics (chi², correlation, runtime)
- **Confidence:** HIGH (~90%) Phase 0 will succeed (target functions are known to exist per TORCH-GEOMETRY-CONVERGENCE-001, variance loss is validated per PHYSICS-LOSS-001)

**Path B (Phase 0 PARTIAL — Coverage 60-79%, Tests Pass):**
- **Next Actions:** Identify uncovered branches (coverage report analysis), add edge case tests OR accept 60%+ as "good enough" gate per implementation floor pragmatism
- **Fallback:** Lower gate to 60% if uncovered branches are unreachable (CUDA-only, deprecated paths)
- **Confidence:** MEDIUM (~70%) can achieve 80% without major issues

**Path C (Phase 0 BLOCKED — Regression Tests Fail):**
- **Next Actions:** If CUDA error (ENV-CUDA-001), defer regression baseline to env resolution, continue Phase 0 on CPU-only tests, mark ARCH-REFACTOR-001 partially blocked (implementation can proceed, validation deferred)
- **Escalation:** If tests fail for NEW reason (not ENV-CUDA-001), investigate root cause, mark ARCH-REFACTOR-001 blocked, return to Galph
- **Confidence:** LOW (~40% risk of ENV-CUDA-001 carryover, but CPU-only path mitigates)

**Path D (Phase 0 FAIL — Tests Don't Pass Against Current Code):**
- **Next Actions:** Debug test logic (wrong function signatures, incorrect assertions), fix tests, retry
- **Fallback:** If CURRENT code doesn't match spec, mark finding and either (a) fix code first, or (b) adjust test to match current behavior, document discrepancy
- **Confidence:** VERY LOW (~10% risk, functions are known to work per existing smoke tests)

## Findings Applied

- **POLICY-001:** Environment Freeze (Phase 0 tests are dbex-only, no env changes)
- **PHYSICS-LOSS-001:** Variance-weighted loss + sigma_floor clamping (0.2 test spec)
- **PHYSICS-LOSS-003:** Chi-squared consistency (regression baseline metrics)
- **GEOMETRY-003:** Baseline misset derivation, B_ideal convention (0.1 test spec)
- **REFINE-001:** LBFGS scale warm-start patterns (not directly tested in Phase 0, but regression baseline preserves)
- **GRADIENT-001:** Autograd graph preservation (loss function tests use torch.no_grad() for synthetic fixtures, no gradient checks in Phase 0)

## References

- **Implementation Plan:** plans/active/ARCH-REFACTOR-001/implementation.md (lines 77-89 Phase 0 checklist)
- **Spec:** docs/spec-db-workflow.md §6-7 (engine contract, variance definition)
- **Spec:** docs/spec-db-core.md (variance formula, sigma_floor)
- **Spec:** docs/config_crosswalk.md (Crystal Geometry Mapping, MOSFLM A*)
- **Finding:** docs/findings.md PHYSICS-LOSS-001 (variance metadata), GEOMETRY-003 (B_ideal)
- **Code:** dbex/nanobrag_bridge.py (derive_u_matrix_from_mosflm_a_star location)
- **Code:** dbex/nanobrag_refinement.py (_compute_variance_weighted_loss location)
- **Test Registry:** docs/TESTING_GUIDE.md §2 (will add Phase 0 selectors after implementation)
- **Test Registry:** docs/development/TEST_SUITE_INDEX.md (will add Phase 0 entries after implementation)

## Next Actions

**For Ralph (next loop i=253):**
1. Read this planning analysis + implementation.md Phase 0 checklist
2. Locate target functions (grep for derive_u_matrix, _compute_variance_weighted_loss)
3. Create test files (test_geometry_current.py, test_physics_loss_current.py)
4. Implement 0.1 test (derive_u_matrix_roundtrip with 3 assertions)
5. Implement 0.2 test (variance_weighted_loss_sigma_floor with 4 test cases)
6. Run coverage check (0.3), analyze report
7. Run regression baseline (0.4), archive logs
8. Decision synthesis (4-path template), write summary.md with Turn Summary
9. Commit all artifacts (tests, logs, coverage report, decision.md, summary.md)

**Expected Outcome:** Path A (Phase 0 PASS) with ≥80% coverage, regression baseline established, ready for Phase A physics extraction planning

## Conclusion

Phase 0 is a **low-risk, high-value** starting point for ARCH-REFACTOR-001:
- Validates test-writing discipline before investing in refactoring
- Establishes safety net (tests against CURRENT code become parity validators for Phase A)
- Regression baseline captures metrics before any code movement
- Estimated 1 loop (~3.5 hours) with HIGH confidence (90%) of success

**Recommendation:** APPROVE Phase 0 ready_for_implementation for next Ralph loop (i=253).
