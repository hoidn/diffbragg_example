# Supervisor Handoff — TORCH-GEOMETRY-CONVERGENCE-001 Phase B1 Validation Completion

## Summary
Complete LBFGS Test B1 validation to confirm B_ideal mismatch fix resolves catastrophic convergence failure.

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — regression guard (already PASSED in prior loop)

## Artifacts
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/

## Do Now

**Checklist Items:** Phase B1 (Test 1 - LBFGS validation completion)

**Context:** Ralph's Phase B deep diagnostic (commit e86fd4e, 2025-11-22T180000Z) **successfully identified and fixed** the B_ideal source mismatch bug via code audit. Root cause: `dbex/nanobrag_refinement.py:786` was discarding `B_ideal_reciprocal_np` from `derive_u_matrix_from_mosflm_a_star` and recomputing from cctbx (lines 801-818), causing `U @ B_ideal_cctbx ≠ A*_MOSFLM` → catastrophic chi²=1.425B. Fix: line 787 captures both U and B_ideal, line 799 uses returned B_ideal, deleted cctbx code (-9 lines). Zero-point validation PASSED (chi²=989,811). **HOWEVER**, LBFGS optimization loop validation is **INCOMPLETE** (revalidation/stage_a_lbfgs_fixed.log only 77 lines, no telemetry/block_dof_results.json). **Current state:** Fix implemented and zero-point healthy, but NO EVIDENCE that optimization loop chi² step 0 dropped from 1.425B → ~1M.

**Objective:** Execute DECISIVE LBFGS validation test to confirm B_ideal fix resolves catastrophic chi² at step 0 in optimization loop.

### Step 1: Complete LBFGS Test B1 Validation (3 steps, 30min timeout)

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1800 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 3 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/lbfgs_validation/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/lbfgs_validation.log
```

**Rationale:** 3 steps (not 10) — Step 0 chi² is critical fix validation; full convergence can be Phase C. Estimated ~15-20 min.

**Success Criteria:**
- Zero-point: chi² ≈ 989k (unchanged)
- **LBFGS step 0: chi² < 2M** (target ~1M, proving 1000× improvement from pre-fix 1.425B)
- Steps 1-2: chi² stable/improving (trend check)

### Step 2: Extract Validation Metrics

```bash
echo "=== Zero-Point Validation ===" | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/validation_metrics.txt
jq '{chi_squared_initial_mapping, chi_squared_after_stage_a, relative_diff, corr_median_vs_mapping: .summary.corr_median_vs_mapping}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/lbfgs_validation/zero_point_check.json \
  | tee -a plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/validation_metrics.txt

echo -e "\n=== LBFGS Step 0 Chi² (KEY FIX VALIDATION) ===" | tee -a plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/validation_metrics.txt
jq '.chi_squared' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/lbfgs_validation/telemetry/telemetry_step_000.json \
  | tee -a plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/validation_metrics.txt

echo -e "\n=== LBFGS Steps 1-2 Chi² Trend ===" | tee -a plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/validation_metrics.txt
jq '.chi_squared' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/lbfgs_validation/telemetry/telemetry_step_001.json \
  2>/dev/null | tee -a plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/validation_metrics.txt || echo "Step 1 telemetry missing" | tee -a plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/validation_metrics.txt

echo -e "\n=== Test Log Tail ===" | tee -a plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/validation_metrics.txt
tail -20 plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/lbfgs_validation.log \
  | tee -a plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/validation_metrics.txt
```

### Step 3: Synthesize Phase B1 Decision

Use Write tool to create `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/phase_b1_validation_decision.md`

**Decision Paths:**
- **Path A (Fix SUCCESS):** Step 0 chi² < 2M → Fix confirmed, proceed to Phase C
- **Path B (Fix INCOMPLETE):** Step 0 chi² > 10M → Fix didn't work, escalate to instrumentation
- **Path C (Test INCOMPLETE):** Step 0 telemetry missing → Timeout/error, rerun or alternative

**Document must include:**
- Root cause (Scenario C, dbex/nanobrag_refinement.py:786-799 bug)
- Fix (commit e86fd4e, capture B_ideal from derive_u_matrix_from_mosflm_a_star)
- Validation results (zero-point chi², LBFGS step 0 chi², trend)
- Decision path with rationale and confidence
- Next actions

### Step 4: Update Implementation Plan

Edit `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` Phase B checklist line B1:
- Mark `[x]` if Path A, or `[~]` if Path B/C
- Add verdict summary from decision doc

### Step 5: Write Summary

Create `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/summary.md` with Turn Summary format (3-5 sentences):
- Validation test execution
- Main outcome (Step 0 chi², Path verdict)
- Next step (Phase C or deeper diagnostic)
- Artifacts pointer

### Step 6: Commit and Push

```bash
git add -A
git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase B1 validation: [Path A/B/C verdict] - LBFGS step 0 chi²=[VALUE] (tests: regression guard PASSED)"
git push
```

## How-To Map

See Do Now steps above for exact commands.

## Pitfalls To Avoid

1. **Accepting zero-point as sufficient** — Must have LBFGS step 0 telemetry
2. **Expecting full convergence** — Goal is Step 0 ~1M validation, not 10-step convergence
3. **Misinterpreting partial improvement** — Step 0 chi² 5M is NOT success, must be < 2M
4. **Premature Phase C** — Validation + decision + commit only, no Phase C this loop

## If Blocked

**If timeout before Step 0 telemetry:**
- Check log progress (HKL grids? Line search?)
- If slow but progressing: Choose Path C, recommend 2-step or GPU
- If stuck/error: Check log for exceptions

**If Step 0 chi² is 1.425B:**
- Verify fix: `grep "fractionalization_matrix" dbex/nanobrag_refinement.py` → zero active uses
- Check bytecode: `find . -name "nanobrag_refinement.pyc" -delete` and rerun
- If fix active but unchanged: Path B, recommend instrumentation

## Findings Applied

- **CONVERGENCE-001 Phase A (826f4c9)**: derive_u_matrix_from_mosflm_a_star fixed
- **CONVERGENCE-001 Phase B (e86fd4e)**: B_ideal in LBFGS closure fixed; optimization validation PENDING

## Pointers

- **Prior Diagnostics:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/
- **Fix Commit:** e86fd4e
- **Implementation Plan:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md
- **Production Code:** dbex/nanobrag_refinement.py:784-799
