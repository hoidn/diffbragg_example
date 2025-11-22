# Ralph Work Order — TORCH-GEOMETRY-PARITY-003 Phase A Complete → Decisive Convergence Verification

## Summary
Re-run PARITY-002 Phase C2/C3 convergence tests with quaternion U-matrix parameterization using the CURRENT canonical `refGeom.expt` (which has det(U)=1.0) to determine if the catastrophic failures were file-specific or represent a deeper convergence issue.

## Mode
Parity

## Focus
TORCH-GEOMETRY-PARITY-003 — Investigate det(U)≠1 Root Cause & Implement Hybrid Parameterization

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, Active)

## Artifacts
`plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/`
- `parity_probe_current_file.json` — Parity metrics for current refGeom.expt with U-matrix mode
- `phase_c2_convergence_verification.json` — Phase 5 A_scale_only convergence metrics
- `phase_c3_convergence_verification.json` — Phase 5 D_full convergence metrics
- `decision.json` — Final decision (close_parity_003_resolved vs escalate_to_convergence_debugging)
- `pytest_stage_a_regression.log` — Regression guard output
- `commands.txt` — Exact commands executed

## Do Now

Ralph completed Phase A root cause investigation with a **decisive finding**: The det(U)=1.000557 anomaly reported in PARITY-002 Phase C1 **does NOT exist** for the canonical `refGeom.expt` currently in the workspace. Phase A1 dxtbx audit proves `det(U) = 1.0` (within machine precision 1e-16). The discrepancy is due to PARITY-002 using a **different experiment file** with different unit cell parameters (~0.1% volume difference).

**Critical Implication:** With det(U)=1.0, the raw U-matrix is already in SO(3), so the quaternion U-matrix parameterization should achieve perfect parity AND converge successfully (no volume scaling to discard during SO(3) projection). The PARITY-002 Phase C2/C3 catastrophic failures (CC→-0.045, χ²→1.43B) may have been **file-specific artifacts** of the non-canonical experiment with det(U)≠1.

**Your Task:** Execute Ralph's recommended Option 1 verification test to determine whether the quaternion U-matrix approach works with the CURRENT canonical file:

### 1. Extend Parity Probe for Current File Verification

**File:** `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py`

**Action:** Run the existing parity probe with `--use-u-matrix` flag on the CURRENT `refGeom.expt` to confirm:
- Raw U-matrix achieves perfect parity (max_abs_diff < 1e-17, matching Phase A1 audit)
- det(U) ≈ 1.0 within machine precision
- Quaternion parameterization does NOT degrade parity (should remain < 1e-17, unlike PARITY-002's ~4e-05 degradation with det(U)=1.000557)

**Expected Output:** `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/parity_probe_current_file.json`

**Validation:** `max_abs_diff < 1e-6` (strict), `det(U)` within [0.999999, 1.000001]

### 2. Phase C2 Convergence Verification (A_scale_only)

**File:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`

**Action:** Run Phase 5 convergence test with quaternion U-matrix mode:
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --phases 5 --device cpu --adam-steps 10 \
  --use-u-matrix \
  --dof-variants A_scale_only \
  --out-dir plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/
```

**Expected Output:** `phase_c2_convergence_verification.json` (extract A_scale_only metrics from `block_dof_results.json`)

**Success Criteria:**
- Median ROI CC ≥ 0.99 after 10 Adam steps
- χ² drift ≤ 0.5% (stable or improving)
- No NaN/inf in parameters or gradients

**Failure Indicators:**
- CC collapse (< 0.95)
- χ² explosion (> 2× initial)
- Gradient pathology (NaN, inf, or magnitude > 1e10)

### 3. Phase C3 Convergence Verification (D_full)

**Action:** Run Phase 5 with D_full variant:
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --phases 5 --device cpu --adam-steps 10 \
  --use-u-matrix \
  --dof-variants D_full \
  --out-dir plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/
```

**Expected Output:** `phase_c3_convergence_verification.json` (extract D_full metrics from `block_dof_results.json`)

**Success Criteria:**
- Monotonic χ² improvement (each step ≤ previous step's χ²)
- Median CC ≥ 0.99 after 10 steps
- No large CC collapses (no ROI with CC drop > 0.1)

### 4. Synthesize Decision

**File:** `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/decision.json`

**Decision Tree:**

**IF** parity probe shows max_abs_diff < 1e-6 AND det(U) ≈ 1.0 AND A_scale_only converges (CC ≥ 0.99, χ² stable) AND D_full converges (monotonic improvement):
```json
{
  "decision": "close_parity_003_resolved",
  "rationale": "Quaternion U-matrix parameterization achieves <1e-6 parity and converges successfully with canonical refGeom.expt (det(U)=1.0). PARITY-002 Phase C2/C3 failures were file-specific artifacts of using non-canonical experiment with det(U)=1.000557. No hybrid parameterization needed.",
  "next_actions": [
    "Mark TORCH-GEOMETRY-PARITY-003 status=done with finding that det(U) problem was file-specific",
    "Mark TORCH-GEOMETRY-PARITY-002 status=done (quaternion approach validated with det(U)=1.0)",
    "Unblock TORCH-REFINE-002E and update with finding that quaternion U-matrix resolves zero-point geometry discontinuity",
    "Update GEOMETRY-003 finding or create GEOMETRY-004 documenting quaternion U-matrix parameterization conventions"
  ]
}
```

**ELSE IF** parity probe succeeds BUT convergence fails (A_scale_only OR D_full):
```json
{
  "decision": "escalate_to_convergence_debugging",
  "rationale": "Parity is correct (<1e-6) with det(U)=1.0, but convergence still fails. Root cause is NOT geometry encoding but optimizer/loss/gradient pathology. Need dedicated convergence debugging initiative.",
  "next_actions": [
    "Mark TORCH-GEOMETRY-PARITY-003 status=blocked (parity solved, convergence blocked)",
    "Create new initiative TORCH-GEOMETRY-CONVERGENCE-001 to investigate: (a) Adam optimizer hyperparameters, (b) variance-weighted loss numerical stability, (c) gradient flow issues (NaN/inf, exploding/vanishing), (d) quaternion parameterization gradient quality",
    "Capture convergence failure artifacts (parameter trajectories, gradient norms, loss components) for CONVERGENCE-001 Phase A evidence"
  ]
}
```

**ELSE** (parity probe fails):
```json
{
  "decision": "blocked_investigate_parity_regression",
  "rationale": "Parity probe failed (max_abs_diff > 1e-6) despite Phase A1 audit showing det(U)=1.0. Implementation bug or probe configuration error. Need to diagnose before proceeding to convergence tests.",
  "next_actions": [
    "Review probe_crystal_matrix_parity.py implementation for bugs in U-matrix path",
    "Validate quaternion conversion ops (matrix_to_quaternion, quaternion_to_matrix) with unit tests",
    "Check if probe is using the same refGeom.expt as Phase A1 audit"
  ]
}
```

**Template Fields (all paths):**
- `parity_max_abs_diff`: float
- `det_u_measured`: float
- `a_scale_only_final_cc`: float (median ROI CC after 10 steps)
- `a_scale_only_chi2_drift_percent`: float (% change from initial)
- `d_full_monotonic_improvement`: bool
- `d_full_final_cc`: float
- `convergence_failure_mode`: str ("none" | "cc_collapse" | "chi2_explosion" | "gradient_pathology" | "timeout")

### 5. Regression Guard

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
```

**Expected:** PASSED

**If FAILED:** Diagnose whether failure is due to U-matrix path bugs or unrelated regression; document in blocker.md before returning.

### 6. Update Findings (Conditional on Decision)

**IF decision == "close_parity_003_resolved":**
- Update `docs/findings.md` with GEOMETRY-004 (or extend GEOMETRY-003) documenting quaternion U-matrix conventions, det(U)=1.0 validation, and convergence success metrics
- Include note that prior det(U)=1.000557 observation was file-specific and does not apply to canonical workspace

**IF decision == "escalate_to_convergence_debugging":**
- Defer findings update to CONVERGENCE-001 (capture convergence failure evidence only)

## How-To Map

### Parity Probe (Step 1)
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py \
  --device cpu \
  --use-u-matrix \
  --out-dir plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/
```
**Output:** `crystal_matrix_parity.json` → copy to `parity_probe_current_file.json`

### Phase C2 Convergence (Step 2)
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --phases 5 --device cpu --adam-steps 10 \
  --use-u-matrix \
  --dof-variants A_scale_only \
  --out-dir plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/
```
**Timeout:** 1200s (20 minutes, same as PARITY-002 reduced-scope run)
**Output:** `block_dof_results.json` → extract A_scale_only metrics to `phase_c2_convergence_verification.json`

### Phase C3 Convergence (Step 3)
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --phases 5 --device cpu --adam-steps 10 \
  --use-u-matrix \
  --dof-variants D_full \
  --out-dir plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/
```
**Timeout:** 1200s
**Output:** `block_dof_results.json` → extract D_full metrics to `phase_c3_convergence_verification.json`

### Decision Synthesis (Step 4)
Create `decision.json` per decision tree template above, populating all required fields from probe + convergence results.

## Pitfalls To Avoid

1. **File Confusion:** Ensure ALL scripts use the canonical `refGeom.expt` in the workspace root. Do NOT use hardcoded experiment paths or cached files from PARITY-002 runs.

2. **Parity Probe Configuration:** The `--use-u-matrix` flag must trigger the quaternion U-matrix path, NOT the cell+misset path. Verify the probe output includes `path_B_u_matrix` or equivalent U-matrix metrics.

3. **det(U) Validation:** If parity probe reports det(U) ≠ 1.0 (outside [0.999999, 1.000001]), STOP and investigate—this contradicts Phase A1 audit and suggests file confusion or probe bug.

4. **Convergence Timeout:** Phase 5 runs may take 10-15 minutes due to HKL grid builds. Do NOT reduce `--adam-steps` below 10 or skip variants—we need decisive evidence for both A_scale_only AND D_full.

5. **Gradient Monitoring:** If convergence fails, capture gradient norms and parameter trajectories in the decision.json rationale field. Include specific failure mode (cc_collapse, chi2_explosion, gradient_pathology).

6. **Decision Ambiguity:** If results are borderline (e.g., CC = 0.98, just below 0.99 threshold), document in decision.json and recommend supervisor review before closing PARITY-003 or escalating.

7. **Environment Freeze:** Do NOT attempt to install packages or modify CUDA/torch. If imports fail, treat as blocker per CLAUDE.md environment freeze policy.

8. **Findings Timing:** Only update `docs/findings.md` if decision == "close_parity_003_resolved". Do NOT create GEOMETRY-004 if escalating to CONVERGENCE-001.

9. **Protected Assets:** Do NOT modify `dbex/nanobrag_bridge.py` quaternion conversion ops (matrix_to_quaternion, quaternion_to_matrix) implemented in PARITY-002 Phase B. Only call them, do not edit.

10. **Regression Scope:** `test_stage_a_expansion` MUST pass regardless of U-matrix path results. If it fails, diagnose before synthesizing decision (regression takes priority).

## If Blocked

**Parity Probe Fails (max_abs_diff > 1e-6):**
- Capture probe output in `blocker.md`
- Check if probe is using the same `refGeom.expt` as Phase A1 audit (compare cell parameters in JSON)
- Validate quaternion conversion roundtrip with a minimal unit test
- Mark initiative `blocked` in Attempts History with exact parity metrics

**Convergence Timeout (>20 min per variant):**
- Kill the run, capture partial logs in `timeout.md`
- Document HKL grid build count and wall time in decision.json
- Recommend supervisor review timeout threshold or explore HKL caching strategies

**Regression Guard Fails:**
- Capture pytest output in `regression_failure.md`
- Diagnose whether failure is due to U-matrix path (new in this loop) or unrelated change
- Mark `blocked` if regression root cause is unclear; do NOT proceed to decision synthesis

**Import Errors:**
- Record exact error signature in `blocker.md`
- Mark PARITY-003 `blocked` with environment dependency note per CLAUDE.md environment freeze policy
- Do NOT attempt `pip install` or modify sys.path

## Findings Applied (Mandatory)

### From docs/findings.md

**GEOMETRY-001** (Detector Mapping): Adhered—this task uses mapping MOSFLM A* as the geometry source for Stage A initialization, consistent with the detector-aligned coordinate system.

**GEOMETRY-002** (Euler Inversion): Adhered—quaternion U-matrix parameterization bypasses Euler angle singularities entirely by working directly in SO(3) manifold.

**GEOMETRY-003** (B_ideal-based Mapping Misset): Superseded—Phase A proves the baseline misset approach cannot eliminate the 1.37e-3 symmetric strain. Quaternion U-matrix is the proposed alternative pending convergence validation.

**DXTBX-001** (dxtbx Crystal API): Adhered—Phase A1 audit used `crystal.get_A()` and `crystal.get_unit_cell()` per DXTBX-001 conventions. Confirmed dxtbx `get_B()` exists and matches cctbx B_ideal.

**REFINE-001** (LBFGS Scale Warm-Start): Adhered—A_scale_only variant tests scale-only refinement with quaternion U-matrix frozen, consistent with warm-start strategy.

**PHYSICS-LOSS-001** (Variance-Weighted Loss): Adhered—all convergence tests use variance-weighted chi-squared with detached denominator per PHYSICS-LOSS-001 normative spec.

**Phase A Root Cause Finding** (PARITY-003 2025-11-22T121500Z): **Critical**—det(U)=1.000557 problem does NOT exist for canonical `refGeom.expt` (det(U)=1.0 within 1e-16). The PARITY-002 failures may be file-specific. This verification test is the DECISIVE experiment to determine if quaternion U-matrix works with the correct file.

## Pointers

- **Spec:** `docs/spec-db-workflow.md:150-175` (Stage A mapping zero-point invariant requirement)
- **Spec:** `docs/spec-db-core.md:45-80` (Geometry Mapping normative definition)
- **Spec:** `docs/spec-db-conformance.md` (Mapping-Aligned Initialization clause)
- **Phase A Evidence:** `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/phase_a_root_cause_determination.md:1-236` (full root cause analysis)
- **Phase A Audit:** `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/dxtbx_a_star_cell_audit.json:1-19` (det(U)=1.0 proof)
- **PARITY-002 Failures:** `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/decision.json` (catastrophic convergence with det(U)≠1 file)
- **Quaternion Ops:** `dbex/nanobrag_bridge.py:630-700` (matrix_to_quaternion, quaternion_to_matrix helpers from PARITY-002 Phase B)
- **Testing Guide:** `docs/TESTING_GUIDE.md:1-100` (authoritative pytest selectors and environment flags)
- **Fix Plan:** `docs/fix_plan.md:1-100` (PARITY-003 initiative definition and escalation chain)

## Next Up (Optional)

If you finish early AND all tests pass (close_parity_003_resolved decision):
- Draft GEOMETRY-004 finding entry for `docs/findings.md` documenting quaternion U-matrix conventions (do NOT commit, leave for supervisor review)
- Run extended regression suite `pytest tests/dbex/test_torch_refine_smoke.py -v` to confirm no side effects (optional, not blocking)

If convergence tests fail (escalate_to_convergence_debugging):
- Capture detailed failure artifacts (parameter trajectories CSV, gradient norm plots, loss component breakdown) under `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/convergence_failure/` for CONVERGENCE-001 Phase A evidence

## Doc Sync Plan
Not applicable this loop (no new test selectors authored; existing `test_stage_a_expansion` validated only).
