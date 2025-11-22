# Supervisor Handoff — TORCH-GEOMETRY-CONVERGENCE-001 Phase A Bugfix (B_ideal Mismatch)

## Summary
Fix B_ideal computation mismatch bug causing quaternion U-matrix catastrophic forward model failure (chi²=1.425B at step 0 vs expected ~990k).

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — regression guard (U-matrix path must not break cell+misset default)

## Artifacts
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/

## Do Now

**Checklist Items:** Phase A Bugfix Implementation (refactor derive_u_matrix_from_mosflm_a_star to return B_ideal, update call sites, validate fix)

**Root Cause Confirmed:** Ralph's diagnostic (`forward_model_discrepancy_analysis.md` at 2025-11-22T150000Z) identified decisive bug:
- `derive_u_matrix_from_mosflm_a_star` (dbex/nanobrag_bridge.py:844-862) computes `B_ideal_reciprocal` using TorchCrystal `np.column_stack([a_star, b_star, c_star])`
- `_build_stage_a_components` (stage_a_mapping_adam_debug.py:323-326) independently computes `B_ideal_reciprocal` using cctbx `fractionalization_matrix().reshape(3,3).T`
- These two methods produce slightly different matrices → `U_initial @ B_ideal_cctbx ≠ A_star_mosflm`
- Reconstruction error propagates through simulator → 1000× worse chi-squared (1.425B vs 990k)

**Fix Strategy (Option 2):** Refactor helper to return BOTH U and B_ideal from same TorchCrystal computation, ensuring `U @ B_ideal == A_star` by construction.

### Step 1: Refactor Helper Signature

Edit `dbex/nanobrag_bridge.py` function `derive_u_matrix_from_mosflm_a_star` (line 794):

**Changes:**
1. Change return type from `-> np.ndarray` to `-> Tuple[np.ndarray, np.ndarray]`
2. Add to return statement: `return U, B_ideal_reciprocal` (instead of just `return U`)
3. Update docstring Returns section:
   ```
   Returns:
       Tuple of (U_matrix, B_ideal_reciprocal), both 3×3 numpy arrays (dtype=float64).
       U_matrix: Orientation matrix from A* = U @ B_ideal relationship (may have det ≈ 1 ± ε if strain present).
       B_ideal_reciprocal: Ideal reciprocal cell matrix from TorchCrystal computation (same source as U extraction).

   Notes:
       - CONVERGENCE-001 bugfix: Both U and B_ideal are derived from the SAME TorchCrystal computation
         to ensure numerical consistency when reconstructing A* = U @ B_ideal.
       - Prior to this fix, callers independently computed B_ideal via cctbx, causing reconstruction errors
         and catastrophic forward model chi-squared (1.425B vs expected ~990k).
   ```
4. Add `from typing import Tuple` to imports at top of file if not already present

**Exact edit location:** Line 794 signature + line 880 return statement + docstring section after line 817

### Step 2: Update Call Site #1 (stage_a_mapping_adam_debug.py)

Edit `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` in `_build_stage_a_components` function (~lines 305-326):

**Find this code block (lines 315-326):**
```python
U_matrix = derive_u_matrix_from_mosflm_a_star(A_star_mosflm, cell_params)

# Convert to quaternion
q_initial_np = matrix_to_quaternion(torch.tensor(U_matrix, dtype=torch.float64))
q_initial = torch.tensor(q_initial_np, device=device, dtype=dtype)

# B_ideal is derived from unit cell (same as in derive_u_matrix_from_mosflm_a_star)
# Used for U-matrix → A* reconstruction during optimization
from cctbx import crystal as cctbx_crystal
cctbx_cell = cctbx_crystal.symmetry(unit_cell=cell, space_group_symbol="P1").unit_cell()
B_ideal_reciprocal = torch.tensor(
    cctbx_cell.fractionalization_matrix().reshape(3, 3).T, device=device, dtype=dtype
)
```

**Replace with:**
```python
# Get BOTH U and B_ideal from same TorchCrystal computation (CONVERGENCE-001 bugfix)
# Ensures U @ B_ideal == A_star_mosflm numerically at initialization
U_matrix, B_ideal_reciprocal_np = derive_u_matrix_from_mosflm_a_star(A_star_mosflm, cell_params)

# Convert U to quaternion
q_initial_np = matrix_to_quaternion(torch.tensor(U_matrix, dtype=torch.float64))
q_initial = torch.tensor(q_initial_np, device=device, dtype=dtype)

# Convert B_ideal to torch tensor
B_ideal_reciprocal = torch.tensor(B_ideal_reciprocal_np, device=device, dtype=dtype)

# DELETE the cctbx_cell() code below - no longer needed (CONVERGENCE-001 bugfix)
# Prior bug: cctbx fractionalization_matrix() produced different B_ideal than TorchCrystal,
# causing U @ B_ideal reconstruction to fail (chi²=1.425B vs expected ~990k)
```

**Remove these 4 lines completely (the cctbx block):**
```python
from cctbx import crystal as cctbx_crystal
cctbx_cell = cctbx_crystal.symmetry(unit_cell=cell, space_group_symbol="P1").unit_cell()
B_ideal_reciprocal = torch.tensor(
    cctbx_cell.fractionalization_matrix().reshape(3, 3).T, device=device, dtype=dtype
)
```

### Step 3: Update Call Site #2 (dbex/nanobrag_refinement.py)

Edit `dbex/nanobrag_refinement.py` in `run_nanobrag_refinement` function (~line 779):

**Find this code block:**
```python
U_0 = derive_u_matrix_from_mosflm_a_star(A_star_np, cell_params)
```

**Replace with:**
```python
# Get BOTH U and B_ideal from same TorchCrystal computation (CONVERGENCE-001 bugfix)
U_0, _ = derive_u_matrix_from_mosflm_a_star(A_star_np, cell_params)
# Note: B_ideal is discarded here (not used in this function), but returned for consistency
# with stage_a_mapping_adam_debug.py which DOES need it
```

**Important:** This call site does NOT use B_ideal (only needs U to convert to quaternion), so we destructure with `_` to discard the second return value. Add comment explaining why.

### Step 4: Regression Guard

Run the smoke test to ensure cell+misset default path unaffected:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/pytest_stage_a_regression.log
```

**Expected:** PASSED (cell+misset default path unaffected; U-matrix path experimental and gated by flag)

**If FAILED:**
- Capture full traceback
- Check if failure is in cell+misset path (BLOCKER — revert changes) or U-matrix path (investigate but not blocking)
- Document in blocker artifact and do NOT proceed

### Step 5: Validation Run (Rerun Phase A2)

Rerun the instrumented Phase A2 convergence test with bugfix applied to validate chi-squared at step 0 now matches zero-point check:

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --phases 5 --dof-variants A_scale_only \
  --adam-steps 10 --device cpu \
  --telemetry-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/telemetry/ \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/stage_a_debug_rerun.log
```

**Expected outcomes:**
- Chi-squared at step 0 (from `telemetry/telemetry_step_000.json`) should now be ~990k (matching zero_point_check.json), NOT 1.425B
- Zero-point check should still show perfect parity (corr ≈ 1.0, max_abs_diff ~85 photons)
- Adam optimization may still fail to converge (CC collapse, chi² explosion) — that's OK for this step; we're only validating the INITIALIZATION bugfix
- If all 10 steps captured AND chi² at step 0 is ~990k → bugfix successful
- If chi² at step 0 still 1.425B → bugfix incomplete or wrong hypothesis (escalate to Phase A5 variance analysis)

### Step 6: Extract Validation Metrics

After Step 5 completes, extract key metrics to validate bugfix:

```bash
# Extract zero-point check chi-squared (expected ~990k)
jq -r '.summary.chi2_stage_a' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/zero_point_check.json

# Extract step 0 chi-squared (should now match ~990k, NOT 1.425B)
jq -r '.chi_squared' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/telemetry/telemetry_step_000.json

# Extract step 9 chi-squared (final Adam step; may still be high if convergence fails)
jq -r '.chi_squared' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/telemetry/telemetry_step_009.json

# Check if block_dof_results.json was created (full run completion)
ls -la plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/block_dof_results.json
```

### Step 7: Synthesize Decision

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/phase_a_bugfix_decision.md`:

```markdown
# Phase A Bugfix Decision

## Bugfix Applied
Refactored `derive_u_matrix_from_mosflm_a_star` (dbex/nanobrag_bridge.py:794) to return `Tuple[U_matrix, B_ideal_reciprocal]` instead of just `U_matrix`. Updated 2 call sites to use returned B_ideal instead of independently computing via cctbx. Deleted cctbx fractionalization_matrix code from stage_a_mapping_adam_debug.py:323-326.

## Validation Results

**Zero-Point Check Chi-Squared:** [paste from zero_point_check.json]
**Step 0 Chi-Squared (Post-Bugfix):** [paste from telemetry_step_000.json]
**Chi-Squared Ratio:** [step_0 / zero_point]

**Decision Tree:**

### Path A: Bugfix Resolved Initialization (chi² step_0 ≈ zero_point, ratio < 1.1)
- **Verdict:** B_ideal mismatch bug FIXED. Forward model correct at initialization.
- **Next Phase:** Proceed to Step 8 convergence analysis (did Adam optimization succeed or still fail?)
- **Recommended Action:**
  - If Step 9 chi² improved AND median CC ≥ 0.99 → Mark Phase A complete, proceed to Phase C validation (C2/C3 full DoF convergence tests)
  - If Step 9 chi² still exploded OR CC collapsed → Adam optimization still fails DESPITE correct initialization → Escalate to Phase B hypothesis testing (H1: Adam hyperparameters, H2: variance instability)

### Path B: Bugfix Incomplete (chi² step_0 still >> zero_point, ratio > 10)
- **Verdict:** B_ideal bugfix did NOT resolve initialization discrepancy. Wrong hypothesis or implementation error.
- **Next Actions:**
  1. Verify bugfix was applied correctly (check git diff, confirm both call sites updated, cctbx code deleted)
  2. Add debug logging to print A_star_mosflm, U_matrix, B_ideal_reciprocal, A_star_reconstructed at step 0
  3. Check reconstruction error: ||U @ B_ideal - A_star_mosflm||
  4. If reconstruction error > 1e-3 → Implementation bug in refactored helper (check TorchCrystal cell construction)
  5. If reconstruction error < 1e-6 BUT chi² still high → Escalate to Phase A5 variance analysis (variance denominator pathology)
- **Recommended Action:** Document findings in blocker artifact, do NOT proceed to Phase C

### Path C: Partial Improvement (chi² step_0 improved but still higher than zero_point, 1.1 < ratio < 10)
- **Verdict:** Bugfix partially resolved issue but reconstruction still imperfect.
- **Next Actions:**
  1. Add debug logging per Path B to measure reconstruction error
  2. Check if cctbx code was fully deleted (might be residual path using old computation)
  3. Validate TorchCrystal cell parameters match cctbx cell parameters (print both for comparison)
- **Recommended Action:** Document partial fix in phase_a_bugfix_decision.md, investigate residual error source before proceeding
```

**Your task:** Fill in the metrics placeholders with actual values from Step 6, select the appropriate decision path (A/B/C), and document the verdict with confidence level (high/medium/low).

### Step 8 (CONDITIONAL): Convergence Analysis

**Only execute if Step 7 selected Path A (bugfix resolved initialization):**

Analyze whether Adam optimization succeeded or still failed DESPITE correct initialization:

```bash
# Extract final DoF results (if available)
jq -r '.A_scale_only | {final_cc: .median_roi_cc, chi2_ratio: .chi2_ratio}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/block_dof_results.json
```

**Decision criteria:**
- **Convergence SUCCESS:** `final_cc ≥ 0.99` AND `chi2_ratio ≤ 1.05` (chi² stable or improving)
  - Verdict: Bugfix resolved BOTH initialization AND convergence pathology
  - Action: Mark Phase A complete (A0-A3), skip Phase A4-A6 (not needed), proceed directly to Phase C validation (C2 A_scale_only + C3 D_full full DoF tests)

- **Convergence FAILURE:** `final_cc < 0.95` OR `chi2_ratio > 2.0` (chi² exploded)
  - Verdict: Bugfix resolved initialization (step 0 correct) but Adam optimization STILL fails during steps 1-9
  - Action: Escalate to Phase B hypothesis testing (H1: Adam hyperparameters incompatible with quaternion manifold, H2: variance-weighted loss numerical instability during optimization)

- **Inconclusive:** Intermediate metrics or missing block_dof_results.json
  - Action: Rerun Step 5 with extended timeout (2400s) or check for early termination in logs

### Step 9: Update Implementation Plan Checklist

Edit `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`:

**Mark Phase A items complete:**
- [x] A0: Evidence Synthesis — DONE (2025-11-22T134421Z)
- [x] A1: Instrument Quaternion Closure — DONE (2025-11-22T140000Z, commit 3d5c613)
- [x] A2: Execute Instrumented Run — DONE (2025-11-22T152500Z rerun with bugfix applied, chi² step_0 validated)
- [x] A3: First Divergence Analysis — DONE (2025-11-22T150000Z, root cause identified as B_ideal mismatch bug)

**Add bugfix note to A2:**
```markdown
**BUGFIX (2025-11-22T152500Z):** Refactored `derive_u_matrix_from_mosflm_a_star` to return both U and B_ideal from same TorchCrystal computation (commit [SHA]). Eliminated cctbx B_ideal mismatch causing 1000× chi-squared error at initialization. Post-bugfix validation: chi² step_0 = [value from Step 6], matching zero_point_check ~990k (ratio [value]).
```

**Update A4-A6 status based on Step 8 decision:**
- If convergence SUCCESS → Mark A4-A6 as "SKIPPED (bugfix resolved convergence; deep gradient/variance analysis not needed)"
- If convergence FAILURE → Keep A4-A6 as PENDING; transition to Phase B for targeted hypothesis tests

### Step 10: Emit Summary

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/summary.md`:

```markdown
### Turn Summary
[If Path A + convergence SUCCESS:]
Implemented B_ideal mismatch bugfix: refactored derive_u_matrix_from_mosflm_a_star (dbex/nanobrag_bridge.py:794) to return both U and B_ideal from same TorchCrystal computation, updated 2 call sites (stage_a_mapping_adam_debug.py:315, dbex/nanobrag_refinement.py:779), deleted cctbx fractionalization_matrix code. Validation confirmed chi² step_0 now [value] (ratio [value] vs zero_point ~990k). Adam optimization [SUCCEEDED/PARTIAL: final CC=[value], chi²_ratio=[value]]. Regression guard PASSED.
Next: Phase C validation (C2 A_scale_only + C3 D_full full DoF convergence tests with U-matrix parameterization) to confirm exit criteria (CC ≥ 0.99, χ² stable).
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/ (phase_a_bugfix_decision.md, telemetry/*.json, block_dof_results.json, pytest_stage_a_regression.log)

[If Path A + convergence FAILURE:]
Implemented B_ideal mismatch bugfix resolving initialization pathology (chi² step_0 now [value], matching zero_point ~990k). However, Adam optimization STILL fails during steps 1-9 (final CC=[value], chi²=[value]), indicating optimizer/loss numerical instability DESPITE correct forward model at initialization.
Next: Phase B hypothesis testing (test Adam hyperparameters, gradient clipping, loss clamping, LBFGS alternative) to diagnose convergence pathology.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/ (phase_a_bugfix_decision.md, telemetry/*.json, block_dof_results.json, pytest_stage_a_regression.log)

[If Path B (bugfix incomplete):]
Attempted B_ideal mismatch bugfix but chi² step_0 still [value] (ratio [value] vs zero_point ~990k), indicating bugfix incomplete or wrong hypothesis. Verified code changes applied correctly; need deeper instrumentation (debug logging for A_star_mosflm, U, B_ideal, reconstruction error) or escalation to Phase A5 variance analysis.
Next: Add debug logging, rerun validation, investigate reconstruction error source.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/ (phase_a_bugfix_decision.md, stage_a_debug_rerun.log, pytest_stage_a_regression.log)
```

Prepend this to existing `summary.md` (keep Galph 2025-11-22T150000Z and Ralph 2025-11-22T140000Z entries below).

## How-To Map

**Refactor Helper Signature (Step 1):**
```bash
# Edit dbex/nanobrag_bridge.py line 794
# Change: def derive_u_matrix_from_mosflm_a_star(...) -> np.ndarray:
# To:     def derive_u_matrix_from_mosflm_a_star(...) -> Tuple[np.ndarray, np.ndarray]:

# Add import at top of file (if not present):
# from typing import Tuple

# Change line 880 return statement:
# From: return U
# To:   return U, B_ideal_reciprocal

# Update docstring Returns section (after line 817) with CONVERGENCE-001 bugfix notes
```

**Update Call Site #1 (Step 2):**
```bash
# Edit plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py lines 315-326
# Replace U_matrix = derive_u_matrix_from_mosflm_a_star(A_star_mosflm, cell_params)
# With:   U_matrix, B_ideal_reciprocal_np = derive_u_matrix_from_mosflm_a_star(A_star_mosflm, cell_params)

# Convert B_ideal to torch tensor:
# B_ideal_reciprocal = torch.tensor(B_ideal_reciprocal_np, device=device, dtype=dtype)

# DELETE lines 323-326 (cctbx_cell code block)
```

**Update Call Site #2 (Step 3):**
```bash
# Edit dbex/nanobrag_refinement.py line 779
# Replace: U_0 = derive_u_matrix_from_mosflm_a_star(A_star_np, cell_params)
# With:    U_0, _ = derive_u_matrix_from_mosflm_a_star(A_star_np, cell_params)
# Add comment explaining why B_ideal is discarded (not used in this function)
```

**Validation Commands (Steps 4-6):**
```bash
# Step 4: Regression guard
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/pytest_stage_a_regression.log

# Step 5: Rerun Phase A2 with bugfix
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --phases 5 --dof-variants A_scale_only \
  --adam-steps 10 --device cpu \
  --telemetry-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/telemetry/ \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/stage_a_debug_rerun.log

# Step 6: Extract metrics
jq -r '.summary.chi2_stage_a' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/zero_point_check.json

jq -r '.chi_squared' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/telemetry/telemetry_step_000.json
```

## Pitfalls To Avoid

1. **Backward compatibility:** Changing helper signature from `-> np.ndarray` to `-> Tuple[np.ndarray, np.ndarray]` breaks existing call sites. Must update ALL 2 call sites (script + dbex/nanobrag_refinement.py) in same commit. Do NOT commit halfway.

2. **Tuple destructuring:** In dbex/nanobrag_refinement.py, B_ideal is NOT used (only U needed for quaternion conversion). Use `U_0, _ = ...` to discard second return value. Add comment explaining why.

3. **cctbx deletion:** Must FULLY delete the cctbx fractionalization_matrix code (lines 323-326 in script). If you leave it in, the bug persists (B_ideal will be overwritten).

4. **Regression guard environment:** Use exact flags from TESTING_GUIDE.md; do not omit DBEX_SMOKE_SIGMA_SOURCE or DBEX_SMOKE_DETECTOR_SIZE.

5. **Validation run timeout:** 1200s may be insufficient if HKL grid build is slow. If timeout occurs, check logs for progress (e.g., "Building HKL grids for N panels") and extend to 2400s if needed.

6. **Step 0 validation:** Only check chi-squared at step 0 (initialization). Do NOT expect convergence success in Step 5; that's for Step 8 analysis. Bugfix validates INITIALIZATION correctness only.

7. **Missing telemetry files:** If telemetry_step_009.json is missing (same issue as before), check stage_a_debug_rerun.log for early termination. Extract partial results and note in decision.md that full 10-step run incomplete.

8. **Decision path selection:** Be honest in Step 7 decision. If chi² step_0 still high (ratio > 10), admit bugfix failed and select Path B; do NOT force Path A. Galph needs honest data for escalation decisions.

9. **Findings update timing:** Do NOT update docs/findings.md this loop. Findings update happens in Phase C5 after validation confirms bugfix resolves exit criteria. This loop is implementation + validation only.

10. **Protected Assets:** Do not modify `dbex/data_load.py`, `dbex/run_diffbragg.py`, or `dbex/refine_one.py`. Bugfix is scoped to `dbex/nanobrag_bridge.py` helper and its 2 call sites only.

## If Blocked

**If regression guard fails (Step 4):**
- Capture full pytest traceback
- Check if failure is in cell+misset default path (uses `if not config.use_u_matrix_parameterization:` branch)
- If default path broken → REVERT all changes immediately and document blocker
- If U-matrix path broken → Investigate but do NOT revert (U-matrix is experimental, gated by flag)

**If validation run times out (Step 5):**
- Check stage_a_debug_rerun.log for progress indicators (e.g., "Optimizer step 3/10")
- If HKL grid build in progress → Extend timeout to 2400s and rerun
- If crashed mid-run → Capture traceback and check for import errors or CUDA issues

**If chi² step_0 still 1.425B after bugfix (Step 6 Path B):**
- Verify code changes applied correctly:
  ```bash
  git diff dbex/nanobrag_bridge.py
  git diff plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py
  git diff dbex/nanobrag_refinement.py
  ```
- Check that cctbx code was fully deleted (not just commented out)
- Document in blocker: "Bugfix applied but chi² step_0 unchanged; hypothesis incorrect or implementation error"
- Do NOT proceed to Phase C; escalate to Galph for Phase A5 variance analysis

**If block_dof_results.json missing (Step 8):**
- Extract partial metrics from telemetry files (step_000 through step_009)
- Compute convergence trend: plot chi² trajectory across steps
- If chi² monotonically decreases → Partial success (timeout issue, not convergence failure)
- If chi² flat or increases → Convergence failure confirmed
- Document in decision.md with "PARTIAL RUN" note

## Findings Applied (Mandatory)

- **REFINE-001** (LBFGS scale warm-start, NaN/Inf guards): Not directly applicable to initialization bugfix; deferred to Phase B if convergence still fails.
- **PHYSICS-LOSS-002** (variance-weighted chi-squared sigma-floor guard): Relevant to chi² computation but not root cause of B_ideal mismatch.
- **GRADIENT-001** (autograd graph preservation): Not applicable to initialization bugfix (no graph mutations in this fix).
- **GEOMETRY-003** (baseline misset derivation): Not applicable; U-matrix path bypasses misset entirely.
- **GEOMETRY-004** (U-matrix parameterization conventions): Directly applicable — bugfix ensures `U @ B_ideal == A_star` at initialization per GEOMETRY-004 parity requirement.
- **New Finding (Pending):** If bugfix succeeds, create CONVERGENCE-002 documenting B_ideal mismatch bug, fix, and numerical parity validation protocol for U-matrix initialization.

## Pointers

- **Phase A Diagnostic:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/forward_model_discrepancy_analysis.md (root cause diagnosis, Option 2 fix recommendation)
- **Telemetry (Pre-Bugfix):** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/plans/active/.../telemetry/telemetry_step_000.json (chi² = 1.425B)
- **Zero-Point Check:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/zero_point_check.json (chi² = 990k, perfect parity)
- **Implementation Plan:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md (Phase A checklist, A0-A3 status)
- **Fix Plan:** docs/fix_plan.md line 40 (TORCH-GEOMETRY-CONVERGENCE-001 entry, Tier 1 top priority)
- **Spec:** docs/spec-db-workflow.md §Stage A (optimizer convergence), docs/spec-db-core.md §Variance Model (chi-squared definition)
- **Helper:** dbex/nanobrag_bridge.py:794 (derive_u_matrix_from_mosflm_a_star function to refactor)
- **Call Sites:**
  - plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:315 (update to destructure tuple, delete cctbx code)
  - dbex/nanobrag_refinement.py:779 (update to discard B_ideal with `_`)

## Next Up (Optional)

If you finish Step 10 early AND Step 7 selected Path A (bugfix resolved initialization):

**Do NOT proceed to Phase B** (hypothesis testing not needed if convergence succeeded)
**Do NOT proceed to Phase A4-A6** (gradient/variance deep analysis not needed if bugfix resolved issue)

Instead, IF Step 8 shows convergence SUCCESS (final CC ≥ 0.99, chi² stable):
- Prepare for Phase C transition by reading Phase C checklist (C1-C6 in implementation.md)
- Note that Phase C Do Now will include C2 (A_scale_only full validation), C3 (D_full multi-DoF), C4 (regression guard), C5 (findings update CONVERGENCE-002)
- Do NOT implement Phase C this loop; just prep context for next Galph handoff

If Step 8 shows convergence FAILURE (CC collapsed or chi² exploded):
- Read Phase B checklist (B0-B4 in implementation.md)
- Note hypothesis tests: H1 (Adam hyperparameters), H2 (variance instability)
- Prepare context for Phase B Do Now (optimizer alternatives, gradient clipping, loss clamping)

## Doc Sync Plan

Not applicable (no tests added/renamed this loop; bugfix is implementation-only).

If bugfix succeeds and reaches Phase C5 findings update, that loop will include:
- Create CONVERGENCE-002 finding in docs/findings.md documenting B_ideal mismatch bug, TorchCrystal vs cctbx discrepancy, refactored helper fix, and numerical parity validation protocol
- Cross-reference GEOMETRY-004 (U-matrix parameterization) noting initialization parity requirement
