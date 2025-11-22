# Phase C6 — Code Path Divergence Fix Implementation

## Summary
Implement bypass fix to eliminate code path divergence confirmed by Phase C5 diagnostic (793% chi² difference at mapping zero point).

## Mode
TDD

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped tests
- **Active:** `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard)
- **Validation:** Manual rerun of Phase C5 diagnostic (code path equivalence check)
- **Full validation:** Manual 10-step A_scale_only convergence test

## Artifacts
`plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T240000Z/`

## Do Now

Phase C5 diagnostic CONFIRMED catastrophic code path divergence (delta_chi²=+793% at mapping zero point). Zero-point validation path (use_mapping_zero_geometry=True, chi²=989,646) and first closure path (use_mapping_zero_geometry=False, chi²=8,837,165) produce DIFFERENT forward models even when all parameters are at their zero values.

**Root Cause:** The closure path reconstructs A* via `U @ B_ideal` round-trip and passes through `crystal_overrides`, while the zero-point path uses direct MOSFLM A* injection. This round-trip introduces numerical error or triggers different handling in `create_crystal_config`.

**Your task:** Implement Option 1 fix (bypass crystal_overrides at mapping zero point), validate with C5 diagnostic rerun, then execute full convergence test.

### Implementation Steps

1. **Review Phase C5 diagnostic findings:**
   - Read `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232200Z/phase_c5_code_path_divergence_decision.md`
   - Understand Path B verdict (code paths DIVERGE, delta_chi²=793%)
   - Review recommended fix options (§Priority 3, Option 1)

2. **Implement zero-check bypass logic in `_stage_a_forward`:**
   - File: `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`
   - Target function: `_stage_a_forward` (lines ~420-540)
   - Add parameter delta check BEFORE the `if use_mapping_zero_geometry:` conditional (line ~428):

   ```python
   # CONVERGENCE-001 Phase C6: Check if ALL parameter deltas are zero (at mapping zero point)
   # If true, bypass U/B_ideal round-trip and use direct MOSFLM A* injection
   # to avoid numerical precision divergence confirmed by Phase C5 diagnostic.
   all_params_at_zero = True  # Assume true, falsify below

   # Check cell parameter deltas (6 DOF)
   if not torch.allclose(log_cell_a_delta, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
       all_params_at_zero = False
   if not torch.allclose(log_cell_b_delta, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
       all_params_at_zero = False
   if not torch.allclose(log_cell_c_delta, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
       all_params_at_zero = False
   if not torch.allclose(angle_alpha_raw, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
       all_params_at_zero = False
   if not torch.allclose(angle_beta_raw, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
       all_params_at_zero = False
   if not torch.allclose(angle_gamma_raw, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
       all_params_at_zero = False

   # Check orientation parameter delta (4 DOF quaternion for U-matrix, or 3 DOF orientation_vec for cell+misset)
   if components.use_u_matrix:
       # U-matrix path: compare q_params to q_initial
       if q_params is not None and not torch.allclose(q_params, components.q_initial, atol=1e-9):
           all_params_at_zero = False
   else:
       # Cell+misset path: check orientation_vec
       if not torch.allclose(orientation_vec, torch.tensor([0.0, 0.0, 0.0], device=device, dtype=dtype), atol=1e-9):
           all_params_at_zero = False

   # If all deltas are zero AND we're in closure mode, force direct MOSFLM injection
   use_direct_mosflm_injection = use_mapping_zero_geometry or all_params_at_zero
   ```

3. **Replace the `if use_mapping_zero_geometry:` condition:**
   - Change line ~428 from:
     ```python
     if use_mapping_zero_geometry:
     ```
   - To:
     ```python
     if use_direct_mosflm_injection:
     ```
   - This applies the bypass logic without duplicating code

4. **Update telemetry code_path field:**
   - In the `use_direct_mosflm_injection` branch (formerly zero-point path), update:
     ```python
     code_path = "zero_point" if use_mapping_zero_geometry else "closure_bypass_at_zero"
     ```
   - This distinguishes between explicit zero-point check vs zero-detected bypass in telemetry

5. **Rerun Phase C5 diagnostic to validate fix:**
   - Execute same diagnostic as C5:
     ```bash
     python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
       --use-u-matrix \
       --u-matrix-lr 1e-5 \
       --phases 5 \
       --dof-variants A_scale_only \
       --adam-steps 2 \
       --device cpu \
       --telemetry-dir telemetry \
       --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T240000Z/c6_fix_validation \
       --timeout 1200
     ```
   - Expected artifacts: `c6_fix_validation/{zero_point_check.json, telemetry/, block_dof_results_u_matrix.json}`

6. **Extract fix validation metrics:**
   - Create `c6_fix_validation/fix_validation_metrics.txt` with:
     ```
     === Fix Validation Metrics (Phase C6) ===

     Zero-Point Path:
       chi_squared: <from zero_point_check.json>
       correlation: <value>

     First Closure Path (with bypass fix):
       chi_squared: <from telemetry_step_000_init.json>
       a_star_checksum: <value>
       code_path: <should be "closure_bypass_at_zero">

     Divergence Metrics:
       delta_chi_squared: <abs diff>
       delta_chi_squared_pct: <(delta / zero_point) * 100>%

     Fix Validation Verdict:
       [ ] SUCCESS — delta_chi² < 1% (paths now equivalent)
       [ ] PARTIAL — delta_chi² 1-10% (improved but not equivalent)
       [ ] FAIL — delta_chi² > 10% (fix didn't work)
     ```

7. **Synthesize Phase C6 fix decision:**
   - Create `phase_c6_fix_validation_decision.md` with template:
     ```markdown
     # Phase C6 Decision — Code Path Divergence Fix Validation

     **Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
     **Phase:** C6 (Fix Implementation & Validation)
     **Date:** 2025-11-22T240000Z

     ## Verdict

     **[ ] Path A — Fix SUCCESS (delta_chi² < 1%)**
     **[ ] Path B — Fix PARTIAL (1% ≤ delta_chi² < 10%)**
     **[ ] Path C — Fix FAIL (delta_chi² ≥ 10%)**

     **DIAGNOSIS:** <Fill based on metrics>

     ## Evidence Summary

     <Paste fix_validation_metrics.txt>

     ## Next Actions

     ### If Path A (Fix SUCCESS):
     - Execute full Phase 5 A_scale_only convergence test (10 steps)
     - Success criteria: CC ≥ 0.99, chi² drift ≤ 1%
     - If convergence test passes: mark C6 DONE, proceed to findings update
     - If convergence test fails: new pathology discovered, escalate to Phase C7

     ### If Path B (Fix PARTIAL):
     - Investigate residual divergence (1-10% chi² diff)
     - Audit create_crystal_config for numerical precision issues
     - Consider tightening atol in zero-check logic (currently 1e-9)

     ### If Path C (Fix FAIL):
     - Revert bypass fix
     - Escalate to Priority 2: audit create_crystal_config internals
     - Alternative: test LBFGS optimizer (may have different closure behavior)
     ```

8. **Conditional: If Path A, execute full convergence test:**
   - Run 10-step A_scale_only test:
     ```bash
     python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
       --use-u-matrix \
       --u-matrix-lr 1e-5 \
       --phases 5 \
       --dof-variants A_scale_only \
       --adam-steps 10 \
       --device cpu \
       --telemetry-dir telemetry \
       --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T240000Z/c6_convergence_validation \
       --timeout 2400
     ```
   - Extract convergence metrics: chi²_before, chi²_after, median CC, trajectory
   - Success criteria: CC ≥ 0.99, chi² drift ≤ 1% (or CC ≥ 0.95 if gradual improvement visible)

9. **Regression guard:**
   - Run `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -v`
   - Capture to `pytest_regression.log`
   - MUST PASS before marking C6 complete

10. **Update implementation.md checklist:**
    - Mark `C6` as `[x]` if fix validated AND convergence test passed
    - Or `[~]` if fix validated but convergence test failed
    - Add Path verdict (A/B/C) and convergence metrics

11. **Write summary:**
    - Create `summary.md` with Turn Summary format

12. **Commit and push:**
    - `git add -A`
    - `git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase C6: Fix code path divergence via zero-point bypass (tests: test_stage_a_expansion)"`
    - `git push`


## How-To Map

### Zero-Check Logic (atol=1e-9)
```python
# Check if tensor is zero within numerical tolerance
is_zero = torch.allclose(param_tensor, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9)
```

### Quaternion Comparison
```python
# U-matrix path: compare q_params to q_initial
q_at_zero = torch.allclose(q_params, components.q_initial, atol=1e-9)
```

### Metrics Extraction (Python one-liner T0)
```bash
python -c "
import json
zp = json.load(open('c6_fix_validation/zero_point_check.json'))
t0 = json.load(open('c6_fix_validation/telemetry/telemetry_step_000_init.json'))
delta_pct = abs(t0['chi_squared'] - zp['chi_squared_stage_a']) / zp['chi_squared_stage_a'] * 100
print(f'delta_chi²={delta_pct:.2f}%')
print(f'SUCCESS' if delta_pct < 1.0 else ('PARTIAL' if delta_pct < 10.0 else 'FAIL'))
"
```

## Pitfalls To Avoid

1. **Tolerance too tight** — Using atol=1e-12 may fail due to floating-point accumulation; 1e-9 is appropriate for geometry parameters.

2. **Missing orientation check** — Must check BOTH cell deltas (6 DOF) AND orientation deltas (q_params for U-matrix, orientation_vec for cell+misset).

3. **Variable scope** — Ensure `all_params_at_zero` is computed BEFORE the `if use_direct_mosflm_injection:` conditional, not inside it.

4. **Telemetry schema** — Add new `code_path="closure_bypass_at_zero"` value WITHOUT removing existing "zero_point" and "closure" values (backward compatibility).

5. **Regression risk** — The bypass logic affects EVERY closure evaluation at zero deltas, not just first step; ensure it doesn't break gradient flow for non-zero parameters.

6. **Test completion** — If diagnostic times out during HKL grid building, reduce `--adam-steps` to 1 (only need step 0 init telemetry for fix validation).

7. **Convergence test timing** — Full 10-step test may take ~20-30 min on CPU; budget time accordingly.

8. **Metrics precision** — Use `.12e` format for chi² differences to capture sub-1% divergence accurately.

## If Blocked

**Scenario 1: Fix validation shows Path B (partial improvement 1-10%)**
- Document residual divergence in decision
- Investigate whether crystal_overrides path has subtle numerical precision loss
- Consider tightening atol to 1e-12 if parameters are stable enough

**Scenario 2: Fix validation shows Path C (fail, delta_chi² still >10%)**
- Revert bypass fix (git checkout stage_a_mapping_adam_debug.py)
- Mark C6 as BLOCKED
- Escalate to Priority 2: audit create_crystal_config for numerical bugs

**Scenario 3: Fix succeeds but convergence test fails (chi²>8M, CC<0.95)**
- New pathology discovered AFTER fixing initialization divergence
- Document convergence failure in decision
- Mark C6 as [~] with "fix validated but convergence failed" note
- Escalate to Phase C7 (new diagnostic for post-bypass convergence pathology)

**Scenario 4: Regression guard fails**
- Revert all Phase C6 changes
- Investigate what broke (likely: bypass logic incorrectly triggers for non-zero parameters)
- Fix, retest regression guard, then proceed

## Findings Applied

- **CONVERGENCE-001 Phase C5** (code path divergence): This fix directly addresses the 793% chi² divergence root cause
- **CONVERGENCE-001 Phase B5** (B_ideal mismatch): Similar pattern (code path bug fixed by alignment); bypass logic follows same principle
- **GRADIENT-001** (autograd graph preservation): Zero-check uses torch.allclose (no .item() or .numpy()) to preserve gradients
- **REFINE-001** (LBFGS scale warm-start): Not directly applicable (this is closure bug, not optimizer issue)

## Pointers

- **Spec alignment:** `docs/spec-db-workflow.md §Stage A — Optimizer convergence`, `docs/spec-db-runtime.md §Gradient stability`
- **Test selector reference:** `docs/TESTING_GUIDE.md §2.2` (test_stage_a_expansion regression guard)
- **Prior phase:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232200Z/phase_c5_code_path_divergence_decision.md §Priority 3 Option 1`
- **Fix plan row:** `docs/fix_plan.md:44-69` (TORCH-GEOMETRY-CONVERGENCE-001 Attempts History)
- **Implementation plan:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` (Phase C checklist C6)

## Next Up (if you finish early)

- If Path A (fix success) AND convergence test passes: Begin Phase C8 (findings update CONVERGENCE-002)
- If Path A but convergence test reveals new issue: Draft Phase C7 plan for post-bypass diagnostic
- If Path B/C: Prepare Priority 2 audit plan (create_crystal_config numerical precision investigation)
