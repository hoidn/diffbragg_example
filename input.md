# Ralph Input — PERF-WARM-SIM-001 Phase D Fix (Stage C Chi-Squared Initialization)

## Summary
Fix Stage C chi-squared initialization by explicitly freezing Stage A final cell parameters.

## Mode
none

## Focus
PERF-WARM-SIM-001 — Phase D: Stage C Detector Reuse (Implementation: Chi-Squared Fix)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (Phase D validation)

## Artifacts
`plans/active/PERF-WARM-SIM-001/reports/2025-11-24T065000Z/`
- `pytest_stage_c_full.log`, `decision.md`, `summary.md`

## Do Now

**Context:** Phase D D1-D3 code complete (commit 1bdeca3). Ralph's evidence loop (i=251) identified root cause with 95% confidence: Stage C recomputes cell parameters from baseline `crystal` object which may not match the baseline used during Stage A initialization, causing 0.32% chi-squared mismatch (3.2× beyond 0.1% tolerance). See `plans/active/PERF-WARM-SIM-001/reports/2025-11-24T055458Z/stage_c_chi2_investigation.md` for comprehensive analysis.

**Task:** Implement targeted fix (Path A from investigation): explicitly capture Stage A final cell parameters as frozen values and pass to Stage C closure, eliminating dependency on `crystal` object state.

### Steps (9 total)

1. **Read prior analysis:**
   - plans/active/PERF-WARM-SIM-001/reports/2025-11-24T055458Z/stage_c_chi2_investigation.md (root cause + fix specification)
   - dbex/nanobrag_refinement.py:3083-3091 (Stage C cell parameter reconstruction)
   - dbex/nanobrag_refinement.py:4700-4800 (Stage A completion, insertion point for fix)

2. **Compute Stage A final cell parameters** (after Stage A LBFGS completes, before Stage C initialization):
   - **Location:** `dbex/nanobrag_refinement.py` after line ~4700 (Stage A telemetry finalization)
   - **Code:**
     ```python
     # Capture Stage A final cell parameters for Stage C
     with torch.no_grad():
         cell_params_baseline = crystal.get_unit_cell().parameters()
         stage_a_final_cell = {
             'cell_a': (cell_params_baseline[0] * torch.exp(param_values_a['log_cell_a_delta'])).item(),
             'cell_b': (cell_params_baseline[1] * torch.exp(param_values_a['log_cell_b_delta'])).item(),
             'cell_c': (cell_params_baseline[2] * torch.exp(param_values_a['log_cell_c_delta'])).item(),
             'alpha': (cell_params_baseline[3] + torch.tanh(param_values_a['angle_alpha_raw']) * max_angle_delta).item(),
             'beta': (cell_params_baseline[4] + torch.tanh(param_values_a['angle_beta_raw']) * max_angle_delta).item(),
             'gamma': (cell_params_baseline[5] + torch.tanh(param_values_a['angle_gamma_raw']) * max_angle_delta).item(),
         }
     ```
   - **Rationale:** Extract scalar values from tensors using `.item()` to avoid autograd graph retention; these are frozen constants for Stage C.

3. **Pass frozen cell params to Stage C closure** (via `param_values_c` dict):
   - **Location:** `dbex/nanobrag_refinement.py` line ~4862 (param_values_c dict construction)
   - **Add key:** `param_values_c['stage_a_final_cell'] = stage_a_final_cell`
   - **Rationale:** Stage C closure receives frozen values without needing to recompute from baseline crystal.

4. **Modify Stage C closure to use frozen values** (instead of recomputing cell parameters):
   - **Location:** `dbex/nanobrag_refinement.py:3083-3091` (compute_loss_stage_c function)
   - **Current code:**
     ```python
     cell_params = crystal.get_unit_cell().parameters()
     perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
     perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
     perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)
     perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
     perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
     perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta
     ```
   - **New code:**
     ```python
     # Use frozen Stage A final cell parameters (spec: Stage C freezes crystal/scale/Fhkl)
     stage_a_final_cell = param_values.get('stage_a_final_cell')
     if stage_a_final_cell is not None:
         # Frozen values from Stage A (no recomputation)
         perturbed_cell_a = stage_a_final_cell['cell_a']
         perturbed_cell_b = stage_a_final_cell['cell_b']
         perturbed_cell_c = stage_a_final_cell['cell_c']
         perturbed_alpha = stage_a_final_cell['alpha']
         perturbed_beta = stage_a_final_cell['beta']
         perturbed_gamma = stage_a_final_cell['gamma']
     else:
         # Fallback: recompute from baseline (backward compatibility)
         cell_params = crystal.get_unit_cell().parameters()
         perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
         perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
         perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)
         perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
         perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
         perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta
     ```
   - **Rationale:** Eliminates crystal object state dependency; fallback preserves backward compatibility if needed.

5. **Run test_stage_c_detector_microslip:**
   ```bash
   cd /home/ollie/Documents/diffbragg_example
   KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip -v --tb=short > plans/active/PERF-WARM-SIM-001/reports/2025-11-24T065000Z/pytest_stage_c_full.log 2>&1
   ```
   - **Expected outcome:** Test PASSES (Stage C initial chi² == Stage A final chi² within 0.1% tolerance)
   - **If FAIL:** Log error signature, return to Galph for fallback (Path B instrumentation)

6. **Decision synthesis** (4-path template):
   - **Path A (Test PASSES, chi² gap <0.1%):** Fix SUCCESS → Phase D COMPLETE, update implementation.md, commit
   - **Path B (Test FAILS, chi² gap still >0.1%):** Fix INCOMPLETE → investigate parameter capture logic, check if max_angle_delta is defined/accessible
   - **Path C (Test FAILS, different error):** New blocker → log error, return to Galph
   - **Path D (Compilation/import error):** Code bug → fix syntax, re-run

7. **Update implementation.md:**
   - Mark Phase D checklist complete (D1-D4 all done)
   - Add Phase D Status Update section with completion timestamp, chi² fix description

8. **Write summary.md:**
   - Turn Summary (fix outcome, chi² metrics, decision path)
   - Include code locations, test results, next actions

9. **Commit and return:**
   ```bash
   git add plans/active/PERF-WARM-SIM-001/ dbex/nanobrag_refinement.py tests/dbex/test_torch_refine_smoke.py
   git commit -m "PERF-WARM-SIM-001 Phase D: Fix Stage C chi-squared initialization (freeze Stage A final cell params)"
   git push
   ```

## How-To Map

**Stage A final cell capture location:**
After Stage A telemetry finalization (dbex/nanobrag_refinement.py:~4700), before Stage C initialization (line ~4862).

**Stage C closure modification:**
Function `compute_loss_stage_c` (lines 3083-3091), replace cell parameter reconstruction with frozen value lookup.

**Test validation:**
Single pytest selector, expect ~12-15s runtime (Stage C detector microslip smoke), chi² assertion at line 1032 should PASS.

**Expected evidence:**
- Before fix: Stage C initial chi² = 2.918e+08, Stage A final chi² = 2.909e+08, gap 0.32%
- After fix: Stage C initial chi² ≈ 2.909e+08 ± 0.03%, gap <0.1% (assertion passes)

## Pitfalls

1. **max_angle_delta variable scope:** Ensure `max_angle_delta` (typically 10.0 degrees) is accessible in Stage A completion block; if not, define locally or extract from param_values_a context.
2. **param_values_a dict keys:** Verify exact key names (e.g., `log_cell_a_delta` not `log_a_delta`) match code at lines ~1268-1276.
3. **torch.no_grad() context:** Required to prevent autograd graph retention when extracting scalar values with `.item()`.
4. **Fallback branch:** Keep recomputation fallback in Stage C closure for backward compatibility (e.g., if Stage A doesn't populate stage_a_final_cell dict).
5. **Frozen values are scalars:** Use Python float values from `.item()`, NOT tensors (Stage C doesn't refine cell, no gradients needed).
6. **Stage C assertion tolerance:** rel=1e-3 (0.1%), NOT absolute tolerance.

## If Blocked

**Compilation error:** Fix syntax, check param_values dict key access patterns.
**Test still fails (chi² gap >0.1%):** Log actual chi² values, return to Galph with diagnostic artifacts for Path B instrumentation.
**Cannot locate insertion point:** Search for "Stage A telemetry" or "finalize_stage_a" comments around line 4700.

## Findings Applied

PHYSICS-LOSS-003 (variance-weighted chi² consistency), REFINE-009 (Stage C baseline detector seeding), POLICY-001 (Environment Freeze, dbex-only changes), spec-db-workflow.md:62-65 (Stage C spec: Fixed crystal/scale/Fhkl)

## Pointers

- plans/active/PERF-WARM-SIM-001/reports/2025-11-24T055458Z/stage_c_chi2_investigation.md (root cause analysis)
- dbex/nanobrag_refinement.py:3083-3091 (Stage C closure cell parameter reconstruction)
- dbex/nanobrag_refinement.py:4700-4800 (Stage A completion, insertion point)
- dbex/nanobrag_refinement.py:4862-4879 (param_values_c dict construction)
- tests/dbex/test_torch_refine_smoke.py:1030-1034 (chi² assertion)
- docs/spec-db-workflow.md:62-65 (Stage C normative spec)

## Next Up

**If Path A (Test PASSES):**
- Phase D ✓ COMPLETE (D1-D4 all done, chi² fix validated)
- Update docs/fix_plan.md with completion entry
- Return to Galph for next focus selection (Tier 3 initiatives remaining)

**If Path B (Test FAILS):**
- Instrumentation loop: log Stage A final params vs Stage C initial params, identify parameter mismatch
- Estimated effort: 1 additional loop
