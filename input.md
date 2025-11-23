# Ralph Loop Input — TORCH-GEOMETRY-UB-REALIGN-001 Phase C1: Zero-Point Round-Trip Validation

## Summary
Execute DB-AT-026 zero-point validation tests (Tests 1-3) with incremental UB parameterization to confirm zero-point invariant, plus convergence smoke test to verify refinement behavior matches cell+misset path.

## Mode
TDD

## Focus
TORCH-GEOMETRY-UB-REALIGN-001 — Stage A UB Parameterization Realignment

## Branch
integration

## Mapped Tests
- `tests/dbex/test_ub_parameterization_roundtrip.py::test_orientation_zero_point` (Test 1)
- `tests/dbex/test_ub_parameterization_roundtrip.py::test_cell_zero_point` (Test 2)
- `tests/dbex/test_ub_parameterization_roundtrip.py::test_mapping_parity` (Test 3)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard + incremental UB convergence validation)

## Artifacts
`plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/`

## Do Now

**Goal:** Validate that the incremental UB parameterization implemented in Phase B satisfies the zero-point invariant (`U(0)=U₀`, `B(0)=B₀`, `A*(0)=A*_mapping`) and produces convergence behavior equivalent to the default cell+misset path.

**Context:** Phase B (commit 1a0de3a) successfully wired incremental UB parameterization into Stage A closure with 10 trainable DOF (q_delta quaternion, cell log-perturbations + angle deltas). Regression guard `test_stage_a_expansion` PASSED with `use_incremental_ub=False` (default cell+misset path unaffected). Now Phase C must validate the incremental UB path itself against DB-AT-026 acceptance criteria and convergence benchmarks.

### Step 1: Review Phase B Implementation

Read the Phase B artifacts and code changes:
- Commit 1a0de3a diff (`git show --stat 1a0de3a`)
- Implementation: `dbex/nanobrag_refinement.py:817-876` (param initialization), `dbex/nanobrag_refinement.py:1036-1073` (closure wiring)
- Helpers: `dbex/nanobrag_bridge.py` (`derive_orientation_from_quaternion_delta`, `derive_B_from_cell_deltas`, `busing_levy_B_torch`)
- DB-AT-026 tests: `tests/dbex/test_ub_parameterization_roundtrip.py` (Tests 1-4 exist per Phase B4)

### Step 2: Execute DB-AT-026 Tests 1-3 (Zero-Point Round-Trip Validation)

**Run DB-AT-026 Tests 1-3** to verify zero-point invariant with incremental UB parameterization:

```bash
# Set authoritative test environment per docs/TESTING_GUIDE.md
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1

# Test 1: Orientation zero-point (||U(0) - U₀|| < 1e-12)
pytest -vv tests/dbex/test_ub_parameterization_roundtrip.py::test_orientation_zero_point \
  > plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/pytest_db_at_026_test_1.log 2>&1

# Test 2: Cell zero-point (||B(0) - B₀|| < 1e-12)
pytest -vv tests/dbex/test_ub_parameterization_roundtrip.py::test_cell_zero_point \
  > plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/pytest_db_at_026_test_2.log 2>&1

# Test 3: Mapping parity (||A*(0) - A*_mapping|| < 1e-6)
pytest -vv tests/dbex/test_ub_parameterization_roundtrip.py::test_mapping_parity \
  > plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/pytest_db_at_026_test_3.log 2>&1
```

**Expected Outcomes:**
- All three tests MUST PASS (per Phase B Exit Criteria)
- Test logs archived under artifacts directory
- If any test FAILS, extract error message, tolerance violation details, and suspected root cause (e.g., B-matrix derivation bug, quaternion-to-matrix conversion error, MOSFLM injection issue)

### Step 3: Create Incremental UB Convergence Test

**Objective:** Validate that Stage A refinement with `use_incremental_ub=True` achieves ≥0.2% improvement (matching cell+misset path).

**Implementation:**

1. **Duplicate `test_stage_a_expansion`** to create `test_stage_a_expansion_incremental_ub` in `tests/dbex/test_torch_refine_smoke.py`:
   - Copy function body verbatim
   - Modify `RefinementConfig` to add `use_incremental_ub=True`
   - Update docstring to specify incremental UB path validation
   - Keep all acceptance criteria identical (≥0.2% improvement gate, telemetry structure, convergence behavior)

2. **Run incremental UB convergence test:**

```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export DBEX_SMOKE_DETECTOR_SIZE=small
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1

pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion_incremental_ub \
  > plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/pytest_stage_a_incremental_ub.log 2>&1
```

**Expected Outcome:**
- Test MUST PASS with ≥0.2% improvement
- Telemetry structure identical to cell+misset path (scale, cell a/b/c, angles, orientation, convergence status)
- If test FAILS, extract failure mode (convergence stall, gradient pathology, telemetry corruption, regression guard failure)

### Step 4: Regression Guard

Re-run `test_stage_a_expansion` with `use_incremental_ub=False` (default path) to confirm no regressions:

```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export DBEX_SMOKE_DETECTOR_SIZE=small
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1

pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/pytest_stage_a_regression_guard.log 2>&1
```

**Expected Outcome:**
- Test MUST PASS (confirms cell+misset default path unaffected by Phase B code changes)

### Step 5: Extract Validation Metrics

After all tests complete, extract metrics into JSON using inline Python snippet (T0 micro probe per scriptization policy):

```bash
python3 -c "
import json
import sys
import os

# Read test logs and extract pass/fail + key metrics
artifacts_dir = 'plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z'

# Parse pytest logs for PASSED/FAILED status
def get_test_status(log_file):
    if not os.path.exists(log_file):
        return 'NOT_RUN'
    with open(log_file) as f:
        content = f.read()
        if 'PASSED' in content:
            return 'PASSED'
        elif 'FAILED' in content:
            return 'FAILED'
        else:
            return 'ERROR'

metrics = {
    'db_at_026_test_1_orientation_zero_point': get_test_status(f'{artifacts_dir}/pytest_db_at_026_test_1.log'),
    'db_at_026_test_2_cell_zero_point': get_test_status(f'{artifacts_dir}/pytest_db_at_026_test_2.log'),
    'db_at_026_test_3_mapping_parity': get_test_status(f'{artifacts_dir}/pytest_db_at_026_test_3.log'),
    'stage_a_incremental_ub_convergence': get_test_status(f'{artifacts_dir}/pytest_stage_a_incremental_ub.log'),
    'stage_a_regression_guard': get_test_status(f'{artifacts_dir}/pytest_stage_a_regression_guard.log'),
}

# Determine overall verdict
all_passed = all(status == 'PASSED' for status in metrics.values())
metrics['overall_verdict'] = 'PASS' if all_passed else 'FAIL'

with open(f'{artifacts_dir}/phase_c1_validation_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print(json.dumps(metrics, indent=2))
"
```

Capture the exact command and output in `summary.md` under "Micro probes" section (per scriptization T0 policy).

### Step 6: Synthesize Decision

Create `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/phase_c1_decision.md` with:

**Path A: All Tests PASS**
- Mark Phase C1 COMPLETE in implementation.md checklist
- Proceed to Phase C2-C5 next loop (DB-AT-024 parity, findings update, doc sync)
- Confidence: HIGH (~95%) that incremental UB parameterization is production-ready

**Path B: DB-AT-026 Tests FAIL (Zero-Point Violation)**
- Mark Phase C1 BLOCKED
- Root cause: Bug in B1/B2 helpers (quaternion conversion, B-matrix derivation) or initialization logic
- Next actions: Debug zero-point construction, patch helpers, re-run DB-AT-026
- Escalation: If >2 loops without resolution, consult Galph for alternative parameterization

**Path C: Convergence Test FAILS (≥0.2% gate not met or gradient pathology)**
- Mark Phase C1 BLOCKED
- Root cause: Optimizer incompatibility with incremental UB DOFs, gradient flow issue, or closure bug
- Next actions: Capture telemetry (parameter trajectories, gradient norms), compare to cell+misset path
- Escalation: If incremental UB shows systematic convergence disadvantage, consider hybrid approach or deprecate

**Path D: Regression Guard FAILS**
- Mark Phase C1 BLOCKED
- Root cause: Phase B code broke cell+misset default path (branching logic bug, param initialization aliasing)
- Next actions: Revert commit 1a0de3a, audit branching logic, re-implement with isolated code paths
- Escalation: If regression persists, consult Galph for code review

**Required Fields:**
- Chosen path (A/B/C/D)
- Test results summary (5 tests, PASS/FAIL for each)
- Root cause hypothesis (if Path B/C/D)
- Recommended next actions
- Confidence level (HIGH/MEDIUM/LOW)

### Step 7: Update Implementation Checklist

Edit `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md`:
- Mark C1 as `[x]` DONE (if Path A) or `[~]` BLOCKED (if Path B/C/D) with verdict annotation
- If Path A, note "DB-AT-026 Tests 1-3 PASSED, incremental UB convergence validated"
- If Path B/C/D, note blocking issue and required fix

### Step 8: Write Summary

Create `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/summary.md`:

```markdown
### Turn Summary
Executed Phase C1 zero-point validation for incremental UB parameterization with DB-AT-026 Tests 1-3 and convergence smoke test.
[INSERT: Test results summary — e.g., "All 5 tests PASSED (DB-AT-026 Tests 1-3, incremental UB convergence ≥0.2%, regression guard clean)" OR "DB-AT-026 Test 2 FAILED with ||B(0)-B₀||=5.2e-8 (exceeds 1e-12 tolerance); suspected Busing-Levy B-matrix derivation bug"]
[INSERT: Decision path and next actions — e.g., "Proceeding to Phase C2 (DB-AT-024 parity validation)" OR "Debugging busing_levy_B_torch trigonometry in dbex/nanobrag_bridge.py:XYZ"]
Artifacts: plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/ (pytest logs, metrics JSON, decision doc)
```

### Step 9: Commit

```bash
git add -A
git commit -m "TORCH-GEOMETRY-UB-REALIGN-001 Phase C1: Zero-point validation [INSERT: PASS/FAIL] (tests: [INSERT: test status])

[INSERT: 2-3 sentence summary of outcomes and next actions]

Artifacts: plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push
```

## How-To Map

### DB-AT-026 Test Execution
```bash
# Environment setup (per docs/TESTING_GUIDE.md)
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1

# Run individual tests
pytest -vv tests/dbex/test_ub_parameterization_roundtrip.py::test_orientation_zero_point
pytest -vv tests/dbex/test_ub_parameterization_roundtrip.py::test_cell_zero_point
pytest -vv tests/dbex/test_ub_parameterization_roundtrip.py::test_mapping_parity
```

### Incremental UB Convergence Test Creation
```python
# In tests/dbex/test_torch_refine_smoke.py, duplicate test_stage_a_expansion:

@pytest.mark.allow_cli_sigma
def test_stage_a_expansion_incremental_ub(
    refgeom_dataload,
    refinement_inputs,
    hkl_data,
    smoke_detector_size,
    smoke_sigma_source,
):
    """
    Verify Stage A LBFGS refinement with incremental UB parameterization achieves ≥0.2% loss decrease.

    Identical to test_stage_a_expansion but with use_incremental_ub=True to validate
    quaternion-based incremental orientation (ΔR @ U₀) + cell perturbations (logs/angles).
    """
    from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig

    # ... copy test_stage_a_expansion body verbatim ...

    config = RefinementConfig(
        device='cuda:0',
        dtype=torch.float32,
        # ... other params identical ...
        enable_hkl_interpolation=True,
        use_incremental_ub=True,  # <-- ONLY DIFFERENCE
        sigma_readout_provenance=(
            "external_lookup" if smoke_sigma_source == "metadata" else "cli_override"
        ),
    )

    # ... rest of test logic identical ...
```

## Pitfalls To Avoid

1. **Zero-Point Tolerance Strictness:** DB-AT-026 Tests 1-2 require EXTREMELY tight tolerances (1e-12 for U/B, 1e-6 for A*). Floating-point accumulation in `busing_levy_B_torch` or quaternion normalization can trip these gates. Use FP64 for zero-point validation if needed.

2. **Incremental UB Test Isolation:** `test_stage_a_expansion_incremental_ub` MUST be a new function, not a parametrization of the existing test. Otherwise pytest collection will run both paths in the same session and fixture state aliasing can corrupt results.

3. **Device/Dtype Neutrality:** Incremental UB path must preserve device/dtype neutrality per spec-db-runtime.md. Verify `U_current` and `B_current` inherit dtype/device from params (q_delta, delta_log_a/b/c), not hardcoded FP64/CPU.

4. **Branching Logic:** Phase B3 added three code paths (incremental UB, U-matrix, cell+misset). Ensure `if config.use_incremental_ub:` branch is entered when flag=True and NO OTHER branch executes. Print `config.use_incremental_ub` at closure entry if debugging.

5. **Protected Assets:** Do NOT modify:
   - `dbex/nanobrag_bridge.py`: B1/B2 helpers already implemented in Phase B
   - `tests/dbex/test_ub_parameterization_roundtrip.py`: DB-AT-026 Tests 1-4 already exist
   - `dbex/nanobrag_refinement.py:817-876, 1036-1073`: Incremental UB initialization/closure wiring complete
   - Only ADD new convergence test `test_stage_a_expansion_incremental_ub`, do not mutate existing functions

6. **Environment Freeze:** Assume frozen runtime. If any import fails (e.g., `scipy.spatial.transform` missing), treat as blocker and record in `docs/fix_plan.md`. Do NOT prescribe pip install/upgrade.

7. **Normative Math:** Do NOT paraphrase Busing-Levy B-matrix equations or quaternion formulas. Reference exact spec sections:
   - B-matrix derivation: `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/cell_parameterization_design.md`
   - Quaternion-to-matrix: `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/orientation_representation_analysis.md`

8. **Telemetry Structure:** Incremental UB path telemetry MUST match cell+misset telemetry structure (scale, cell a/b/c, angles, orientation, misset_xyz_deg). If telemetry keys differ, convergence test will FAIL on assertion checks.

9. **Regression Guard Mandatory:** ALWAYS run `test_stage_a_expansion` (default cell+misset) AFTER incremental UB tests. If regression guard FAILS, revert all changes immediately — do not proceed to decision synthesis.

10. **Convergence Gate Calibration:** ≥0.2% improvement gate is empirically calibrated per REFINE-006. If incremental UB path shows <0.2% improvement, this is a BLOCKING failure (Path C), not a gate recalibration opportunity.

## If Blocked

**Blocker Scenarios:**

1. **DB-AT-026 Test 1 FAILS (Orientation Zero-Point):**
   - Capture error message and tolerance violation (e.g., `||U(0)-U₀|| = 3.2e-8`)
   - Hypothesis: `derive_orientation_from_quaternion_delta` quaternion normalization or identity check bug
   - Mitigation: Verify `q_delta = [1,0,0,0]` produces `ΔR = I` (3×3 identity matrix)
   - Log blocker in Attempts History with tolerance violation details

2. **DB-AT-026 Test 2 FAILS (Cell Zero-Point):**
   - Capture B-matrix error magnitude and suspected component (a/b/c vs α/β/γ)
   - Hypothesis: `busing_levy_B_torch` trigonometry bug or angle unit conversion (degrees vs radians)
   - Mitigation: Compare `busing_levy_B_torch(a₀, b₀, c₀, α₀, β₀, γ₀)` output to dxtbx `crystal.get_B()`
   - Log blocker with B-matrix diff details

3. **DB-AT-026 Test 3 FAILS (Mapping Parity):**
   - Capture A* error magnitude
   - Hypothesis: MOSFLM a/b/c_star injection bug or A* = U @ B matmul dtype mismatch
   - Mitigation: Verify `A_star_new = U_current @ B_current` matches `A*_mapping = U₀ @ B₀`
   - Log blocker with A* diff details

4. **Convergence Test FAILS (<0.2% improvement):**
   - Capture final improvement percentage and convergence status (early_stop, max_iter, error)
   - Hypothesis: Optimizer incompatibility, gradient pathology, or parameter scale mismatch
   - Mitigation: Capture telemetry (parameter trajectories, gradient norms), compare to cell+misset run
   - Log blocker with telemetry comparison

5. **Regression Guard FAILS:**
   - Revert commit 1a0de3a immediately
   - Hypothesis: Phase B3 branching logic bug (incremental UB code interfering with cell+misset path)
   - Mitigation: Audit `if config.use_incremental_ub:` vs `elif config.use_u_matrix_parameterization:` vs `else:` branching
   - Log blocker with error message and suspected code path

**Fallback Capture:**
- Archive all pytest logs under `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/`
- Create `phase_c1_blocker_report.md` with error messages, suspected root cause, and recommended debug steps
- Mark Attempts History with timestamp, blocker scenario (1-5 above), and next actions
- Do NOT proceed to Phase C2 if ANY test fails; must resolve blockers first

## Findings Applied

**Relevant Finding IDs from docs/findings.md:**

- **CONVERGENCE-001:** Stage A U-matrix refinement diagnostic scripts must detect zero-delta state and bypass U @ B_ideal round-trip. Incremental UB path uses MOSFLM a/b/c_star injection (same as CONVERGENCE-001 bypass fix) so zero-point should be healthy. However, monitor for systematic offset between zero-point check and closure initialization (14.5% acceptable when convergence stable per CONVERGENCE-001).

- **GEOMETRY-003:** Stage-A baseline misset derivation from dxtbx A* relative to nanobrag_torch B_ideal. Incremental UB path does NOT use misset_deg (sets to `None` when MOSFLM injection active), so GEOMETRY-003 conventions do not apply to incremental UB path. Cell+misset default path still uses GEOMETRY-003.

- **REFINE-006:** Canonical refGeom Stage A plateau at ~0.206% improvement. Incremental UB path MUST meet ≥0.2% gate with same dataset; if <0.2%, this indicates optimizer/gradient pathology, not dataset ceiling.

## Pointers

- **Spec (Normative Requirements):**
  - spec-db-core.md:48-68 — Baseline Crystal State, Incremental Parameterization, Zero-Point Invariant, One-Way Construction
  - spec-db-workflow.md:36-45 — Stage A Trainable DOFs (cell logs/angles, quaternion → XYZ), Mapping Zero-Point
  - spec-db-runtime.md:18-28 — UB/A* Round-Trip Test, Prohibited Inverse Decompositions

- **Implementation:**
  - dbex/nanobrag_refinement.py:817-876 — Incremental UB param initialization (q_delta, delta_log_a/b/c, delta_alpha/beta/gamma)
  - dbex/nanobrag_refinement.py:1036-1073 — Incremental UB closure wiring (B1/B2 helpers, A* = U @ B construction, MOSFLM injection)
  - dbex/nanobrag_bridge.py — Helper functions (derive_orientation_from_quaternion_delta, derive_B_from_cell_deltas, busing_levy_B_torch)

- **Testing:**
  - tests/dbex/test_ub_parameterization_roundtrip.py — DB-AT-026 Tests 1-4 (zero-point validation)
  - tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — Regression guard (cell+misset default path)
  - docs/TESTING_GUIDE.md §2 — Active Acceptance Tests (DB-AT-026 entry, if added in Phase C5)

- **Design Artifacts:**
  - plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/phase_a_design_document.md — Comprehensive design with normative requirements synthesis, CONVERGENCE-001 lessons, chosen parameterization formulas, zero-point conditions, spec alignment verification, risk analysis
  - plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/orientation_representation_analysis.md — Quaternion vs Euler vs axis-angle comparison, justification for quaternion choice
  - plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/cell_parameterization_design.md — Busing-Levy B-matrix derivation, log-perturbations for lengths, angle deltas
  - plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/db_at_026_test_spec.md — DB-AT-026 5 tests, acceptance criteria, expected runtime

- **Fix Plan:**
  - docs/fix_plan.md:63-79 — TORCH-GEOMETRY-UB-REALIGN-001 entry with dependencies, status, exit criteria, Attempts History

## Next Up (Optional)

If Ralph finishes Phase C1 early and all tests PASS:
- **Phase C2:** Run DB-AT-024 (mapping parity) with `use_incremental_ub=True` to verify Bragg tensor parity
- **Phase C4:** Add GEOMETRY-004 finding to `docs/findings.md` documenting incremental UB conventions

(Do NOT attempt C2/C4 if ANY Phase C1 test fails; must resolve blockers first.)

## Doc Sync Plan

Not applicable for Phase C1 (evidence-only loop). If tests are added/renamed, defer doc sync to Phase C5 after all validation completes.

## Mapped Tests Guardrail

At least one mapped selector must collect (>0) in `--collect-only`. Verify:

```bash
pytest --collect-only tests/dbex/test_ub_parameterization_roundtrip.py::test_orientation_zero_point
pytest --collect-only tests/dbex/test_ub_parameterization_roundtrip.py::test_cell_zero_point
pytest --collect-only tests/dbex/test_ub_parameterization_roundtrip.py::test_mapping_parity
pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
```

If `test_stage_a_expansion_incremental_ub` does not exist yet (expected, since Ralph will create it in Step 3), that selector collecting 0 is ACCEPTABLE for this loop. After creation, verify it collects 1 before proceeding to execution.
