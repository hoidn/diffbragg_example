# Ralph Input — ARCH-REFACTOR-001 Phase 0 (Test Discipline Baseline)

## Summary
Write unit tests against CURRENT code (derive_u_matrix, variance_weighted_loss) to establish test discipline and safety net before Phase A refactoring.

## Mode
none

## Focus
ARCH-REFACTOR-001 — Phase 0: Test Discipline Baseline (Unit Tests + Coverage Gate + Regression Baseline)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_geometry_current.py::test_derive_u_matrix_roundtrip` (NEW test, 0.1 checklist)
- `tests/dbex/test_physics_loss_current.py::test_variance_weighted_loss_sigma_floor` (NEW test, 0.2 checklist)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression baseline, 0.4 checklist)
- `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` (regression baseline, 0.4 checklist)

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/`
- `pytest_geometry_current.log`, `pytest_physics_loss_current.log` (0.1+0.2 test runs)
- `coverage_phase0/` (HTML coverage report, 0.3 checklist)
- `regression_baseline.log` (0.4 smoke tests)
- `phase_0_decision.md` (gate assessment: PASS/FAIL for ≥80% coverage)
- `summary.md` (Turn Summary with loop metrics)

## Do Now

**Context:** ARCH-REFACTOR-001 now in_progress (UNBLOCKED: TORCH-GEOMETRY-CONVERGENCE-001 done). Phase 0 = prove test-writing discipline before refactoring by writing unit tests against CURRENT code. Read `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/phase_0_planning_analysis.md` for comprehensive scope/risks/decision tree.

**Task:** Implement Phase 0 checklist (implementation.md:80-89): write unit tests (0.1, 0.2), achieve 80% coverage (0.3), run regression baseline (0.4).

### Steps (9 total)

1. **Read planning analysis:**
   - `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/phase_0_planning_analysis.md` (scope, risks, decision tree)
   - `plans/active/ARCH-REFACTOR-001/implementation.md:77-89` (Phase 0 checklist)

2. **Locate target functions:**
   ```bash
   grep -rn "def derive_u_matrix" dbex/nanobrag_bridge.py dbex/nanobrag_refinement.py
   grep -rn "def _compute_variance_weighted_loss" dbex/nanobrag_refinement.py
   # Record actual function names + signatures in decision.md if different from expected
   ```

3. **Create test file: test_geometry_current.py (~60 lines, checklist 0.1)**
   - **Location:** `tests/dbex/test_geometry_current.py` (NEW file)
   - **Test:** `test_derive_u_matrix_roundtrip`
   - **Purpose:** Validate MOSFLM A* → (U, B_ideal) → A* reconstruction within 1e-6 per GEOMETRY-003
   - **Strategy:**
     1. Create synthetic A* matrix from known U (orthogonal, det=1) and B_ideal (upper triangular)
        - Example U: random orthogonal matrix from scipy.stats.ortho_group(3).rvs()
        - Example B_ideal: [[0.036, -0.014, -0.014], [0, 0.033, 0.004], [0, 0, 0.030]] (upper triangular)
        - Compute A* = U @ B_ideal
     2. Call `derive_u_matrix_from_mosflm_a_star(A*)`
     3. Assertions (3 total):
        - Assert U_derived is orthogonal: `np.allclose(U_derived.T @ U_derived, np.eye(3), atol=1e-6)`
        - Assert det(U_derived) == ±1: `np.isclose(np.linalg.det(U_derived), 1.0, atol=1e-6) or np.isclose(np.linalg.det(U_derived), -1.0, atol=1e-6)`
        - Assert A* reconstruction: `np.allclose(U_derived @ B_ideal_derived, A*, atol=1e-6)`
   - **Edge Cases:** Test near-zero cell params (small B_ideal values), handle det(U) sign ambiguity
   - **Fixtures:** Use `@pytest.fixture` for synthetic A* generation (reusable across edge case tests)
   - **Imports:** `import numpy as np, pytest, scipy.stats.ortho_group` (if available, else hardcode orthogonal U)
   - **Docstring:** Encode acceptance criteria (roundtrip within 1e-6, orthogonality, det=±1)

4. **Create test file: test_physics_loss_current.py (~80 lines, checklist 0.2)**
   - **Location:** `tests/dbex/test_physics_loss_current.py` (NEW file)
   - **Test:** `test_variance_weighted_loss_sigma_floor`
   - **Purpose:** Validate variance clamping V = max(I_model + sigma², variance_floor) per spec-db-core.md and PHYSICS-LOSS-001
   - **Strategy:**
     1. Create synthetic target/model/mask tensors (3×3 or 5×5 small arrays)
        - Example: target = torch.tensor([[5.0, 10.0, 3.0], [7.0, 12.0, 8.0], [4.0, 6.0, 9.0]])
        - model = torch.tensor([[4.5, 9.5, 3.2], [6.8, 11.8, 7.9], [4.1, 6.1, 8.9]])
        - mask = torch.tensor([[1.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]])
     2. Call `_compute_variance_weighted_loss(target, model, mask, sigma_readout=1.0, variance_floor=2.0, ...)`
     3. Assertions (4 test cases):
        - **Test case 1 (basic clamping):** Verify variance V = max(model + 1.0², 2.0) per pixel, loss = sum((target-model)²/V * mask) / sum(mask)
        - **Test case 2 (zero mask):** mask=0 everywhere, loss should be 0.0 or NaN with safe handling (no division by zero error)
        - **Test case 3 (zero variance_floor):** variance_floor=0.0, V = model + 1.0 (no clamping), verify loss calculation
        - **Test case 4 (negative model):** model with negative values, verify variance clamping still applies (V = max(..., floor))
   - **Edge Cases:** Large outliers (no overflow), very small sigma_readout (numerical stability)
   - **Fixtures:** Use `@pytest.fixture` for synthetic tensor generation
   - **Imports:** `import torch, pytest, numpy as np` (if function uses torch tensors)
   - **Docstring:** Encode acceptance criteria (variance clamping formula, loss formula, edge case handling)

5. **Run tests and check initial pass status:**
   ```bash
   # Test geometry (0.1)
   pytest -vv tests/dbex/test_geometry_current.py::test_derive_u_matrix_roundtrip \
     > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/pytest_geometry_current.log 2>&1

   # Test physics loss (0.2)
   pytest -vv tests/dbex/test_physics_loss_current.py::test_variance_weighted_loss_sigma_floor \
     > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/pytest_physics_loss_current.log 2>&1
   ```
   - **Expected:** Both tests PASS (tests written against CURRENT code should pass without modifications)
   - **If FAIL:** Debug test logic (wrong function signatures, incorrect assertions), fix tests, retry

6. **Run coverage check (0.3 checklist):**
   ```bash
   pytest --cov=dbex.nanobrag_bridge --cov=dbex.nanobrag_refinement \
     --cov-report=term --cov-report=html:plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/coverage_phase0 \
     tests/dbex/test_geometry_current.py tests/dbex/test_physics_loss_current.py \
     > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/coverage_phase0.log 2>&1
   ```
   - **Target:** ≥80% line coverage for target functions (derive_u_matrix_from_mosflm_a_star, _compute_variance_weighted_loss)
   - **Analysis:** Open `coverage_phase0/index.html`, check per-function coverage (not module-wide)
   - **If <80%:** Identify uncovered branches, add edge case tests OR accept 60%+ as pragmatic gate if uncovered branches are unreachable (CUDA-only, deprecated paths)

7. **Run regression baseline (0.4 checklist):**
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
   - **Expected:** Both tests PASS (establish baseline metrics before Phase A refactoring)
   - **If FAIL (ENV-CUDA-001 carryover):** Note blocker in decision.md, defer regression baseline to env resolution, continue Phase 0 on CPU-only tests (mark partial success)
   - **If FAIL (NEW reason):** Log error signature, return to Galph for investigation

8. **Decision synthesis (4-path template):**
   Write `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/phase_0_decision.md` with:

   - **Path A (Phase 0 PASS — Coverage ≥80%, Regression Baseline Established):**
     - **Verdict:** Phase 0 COMPLETE ✓
     - **Evidence:** coverage_phase0/ report shows ≥80% for target functions, regression_baseline.log shows both tests PASSED
     - **Metrics:** Test counts (geometry: 1+ tests, physics: 1+ tests), coverage % per function, regression runtime/metrics (chi², correlation)
     - **Next Actions:** Ready for Galph Phase A planning (physics extraction scope, A1-A4 checklist, migration strategy)
     - **Confidence:** HIGH (~90%)

   - **Path B (Phase 0 PARTIAL — Coverage 60-79%, Tests Pass):**
     - **Verdict:** Phase 0 MOSTLY COMPLETE (lower gate acceptable)
     - **Evidence:** coverage_phase0/ report shows 60-79% for target functions, uncovered branches are unreachable (CUDA-only, error handling)
     - **Recommendation:** Accept 60%+ as pragmatic gate OR add edge case tests in follow-up loop
     - **Next Actions:** Proceed to Phase A with current test coverage OR add edge case tests first
     - **Confidence:** MEDIUM (~70%)

   - **Path C (Phase 0 BLOCKED — Regression Tests Fail):**
     - **Verdict:** Phase 0 PARTIAL (unit tests PASS, regression baseline BLOCKED)
     - **Evidence:** ENV-CUDA-001 carryover OR new failure signature
     - **Recommendation:** Defer regression baseline to env resolution, continue Phase A on CPU-only path (mark ARCH-REFACTOR-001 partially blocked)
     - **Next Actions:** Escalate env issue OR retry on different session/hardware
     - **Confidence:** LOW (~40%)

   - **Path D (Phase 0 FAIL — Tests Don't Pass Against Current Code):**
     - **Verdict:** Phase 0 BLOCKED (test logic incorrect OR current code doesn't match spec)
     - **Evidence:** test_geometry_current.py FAIL OR test_physics_loss_current.py FAIL
     - **Recommendation:** Debug test assertions (check function signatures, 1e-6 tolerances), fix tests, retry OR mark spec/code discrepancy finding
     - **Next Actions:** Fix test logic OR document code-spec gap
     - **Confidence:** VERY LOW (~10%)

9. **Write summary.md and commit:**
   - **Summary:** `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/summary.md`
     - Turn Summary (3-5 sentences): What shipped (Phase 0 tests), main problem (coverage gate OR env blocker), next step (Phase A planning OR retry)
     - Artifacts line: Point to coverage_phase0/, logs, decision.md
   - **Commit:**
     ```bash
     git add tests/dbex/test_geometry_current.py tests/dbex/test_physics_loss_current.py \
       plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/ plans/active/ARCH-REFACTOR-001/implementation.md
     git commit -m "ARCH-REFACTOR-001 Phase 0: Test discipline baseline — unit tests + coverage gate (tests: run)"
     git push
     ```

## How-To Map

**Function Locations (expected):**
- `derive_u_matrix_from_mosflm_a_star`: dbex/nanobrag_bridge.py (grep "def derive_u_matrix")
- `_compute_variance_weighted_loss`: dbex/nanobrag_refinement.py (grep "def _compute_variance_weighted_loss")

**Test File Templates:**
- Geometry test: ~60 lines (synthetic A* fixture ~15 lines, test function ~25 lines, edge cases ~20 lines)
- Physics test: ~80 lines (synthetic tensor fixtures ~20 lines, test function with 4 cases ~50 lines, docstring ~10 lines)

**Coverage Command:**
```bash
pytest --cov=dbex.nanobrag_bridge --cov=dbex.nanobrag_refinement \
  --cov-report=html:plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/coverage_phase0 \
  tests/dbex/test_geometry_current.py tests/dbex/test_physics_loss_current.py
```

**Regression Baseline Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
```

**Expected Runtimes:**
- Geometry test: <1s (pure numpy operations)
- Physics test: <2s (small torch tensors)
- Coverage check: ~3s (run both tests with coverage instrumentation)
- Regression baseline: ~45s total (Stage A expansion ~12s, DB-AT-024 ~32s)

## Pitfalls

1. **Function Names:** `derive_u_matrix_from_mosflm_a_star` may be named differently (e.g., `derive_u_matrix`). Use grep to locate, adjust test imports.
2. **Test Assertions:** Enforce 1e-6 tolerances (not 1e-3 or default rtol). Tests must validate numerical correctness, not just "doesn't crash".
3. **Coverage Interpretation:** Target 80% per-function line coverage, NOT module-wide. Focus on target functions (derive_u_matrix, _compute_variance_weighted_loss).
4. **Regression Baseline ENV-CUDA-001:** If CUDA error persists, mark Path C (partial success), defer baseline, continue CPU-only. Do NOT attempt env debugging.
5. **Synthetic Fixtures:** Use simple, small arrays (3×3 or 5×5) for physics tests. Avoid large tensors that slow down test execution.
6. **Backward Compatibility:** Tests written against CURRENT code (no production modifications in Phase 0). Phase A will extract functions to new modules; these tests become parity validators.
7. **Edge Cases:** For geometry test, handle det(U) = -1 (both +1 and -1 are valid orthogonal determinants). For physics test, handle zero mask (safe division).

## If Blocked

**Test FAIL (wrong signatures):** Grep for actual function names, check signatures, adjust test imports. Log function locations in decision.md.
**Coverage <80%:** Identify uncovered branches in coverage_phase0/index.html. If unreachable (CUDA-only, error handling), accept lower gate. If reachable, add edge case tests.
**Regression FAIL (ENV-CUDA-001):** Mark Path C (partial success), defer baseline to env resolution, note in decision.md. Continue Phase A planning with caveat (validation deferred).
**Regression FAIL (new error):** Log error signature, return to Galph for investigation (do NOT proceed to Phase A if regression baseline is broken for new reason).

## Findings Applied

- **POLICY-001:** Environment Freeze (Phase 0 tests are dbex-only, no env changes, no package installs)
- **PHYSICS-LOSS-001:** Variance-weighted loss + sigma_floor clamping (0.2 test validates V = max(I_model + sigma², variance_floor) per spec-db-core.md)
- **PHYSICS-LOSS-003:** Chi-squared consistency (regression baseline metrics capture chi² for Phase A comparison)
- **GEOMETRY-003:** Baseline misset derivation, B_ideal convention (0.1 test validates MOSFLM A* = U @ B_ideal reconstruction)
- **REFINE-001:** LBFGS scale warm-start patterns (regression baseline preserves Stage A refinement behavior)
- **GRADIENT-001:** Autograd graph preservation (tests use torch.no_grad() for synthetic fixtures, no gradient checks in Phase 0)

## Pointers

- **Implementation Plan:** plans/active/ARCH-REFACTOR-001/implementation.md:77-89 (Phase 0 checklist)
- **Planning Analysis:** plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/phase_0_planning_analysis.md (comprehensive scope, risks, decision tree)
- **Spec:** docs/spec-db-core.md (variance definition, sigma_floor)
- **Spec:** docs/config_crosswalk.md (Crystal Geometry Mapping, MOSFLM A*)
- **Finding:** docs/findings.md PHYSICS-LOSS-001 (variance metadata), GEOMETRY-003 (B_ideal)
- **Code:** dbex/nanobrag_bridge.py (derive_u_matrix location)
- **Code:** dbex/nanobrag_refinement.py (_compute_variance_weighted_loss location)
- **Test Registry:** docs/TESTING_GUIDE.md §2 (will add Phase 0 selectors AFTER tests pass)
- **Test Registry:** docs/development/TEST_SUITE_INDEX.md (will add Phase 0 entries AFTER tests pass)

## Next Up

**If Path A (Phase 0 PASS):**
- Galph Phase A planning (physics extraction: A1 dbex/geometry/crystallography.py, A2 dbex/geometry/rotations.py, A3 dbex/physics/loss.py, A4 update imports + run Phase 0 tests against NEW locations)
- Estimated effort: 2-3 loops (A1-A2 ~1 loop extraction + validation, A3 ~1 loop extraction + validation, A4 ~1 loop import updates + parity check)

**If Path B (Phase 0 PARTIAL — Coverage 60-79%):**
- Either (a) proceed to Phase A with caveat (tests provide partial safety net), OR (b) add edge case tests in 1 follow-up loop to reach 80%
- Galph decision based on uncovered branch analysis

**If Path C (Phase 0 BLOCKED — Regression Baseline Fails):**
- Defer regression baseline to env resolution
- Proceed to Phase A planning with caveat (validation deferred until env issue resolved)
- Mark ARCH-REFACTOR-001 partially blocked in fix_plan.md

**If Path D (Phase 0 FAIL — Tests Don't Pass):**
- Debug test logic (function signatures, assertions)
- Fix tests in 1 retry loop
- Return to Galph if code-spec discrepancy found
