### Turn Summary
Ralph's evidence loop identified Stage C chi-squared mismatch root cause with 95% confidence: Stage C recomputes cell parameters from baseline crystal object instead of using Stage A frozen final values.
Approved straightforward 1-loop fix: explicitly capture Stage A final cell params as scalar dict after Stage A completion, pass to Stage C closure, eliminate crystal object state dependency.
Next: Ralph implements targeted fix (capture + pass + modify closure), validates test_stage_c_detector_microslip should PASS with chi² gap <0.1%.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-24T065000Z/ (input.md)

---

## Planning Summary

**Focus:** PERF-WARM-SIM-001 Phase D — Stage C Chi-Squared Initialization Fix

**Context:**
- Phase D D1-D3 code complete (commit 1bdeca3)
- Ralph's evidence loop (i=251) delivered comprehensive root cause analysis with 95% confidence
- Problem: Stage C initial chi² (2.918e+08) != Stage A final chi² (2.909e+08), gap 0.94e+06 (0.32%) exceeds tolerance ±2.9e+05 (0.1%)
- Test blocker: test_stage_c_detector_microslip assertion fails at line 1032

**Root Cause (from Ralph's investigation):**
Stage C closure (dbex/nanobrag_refinement.py:3083-3091) recomputes cell parameters by applying Stage A refined deltas to baseline crystal object:

```python
cell_params = crystal.get_unit_cell().parameters()  # ← baseline
perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)  # ← applies Stage A delta
```

**Issue:** The `crystal` object may have been mutated during Stage A, or its baseline values don't match those used during Stage A initialization. This causes Stage C to apply refined deltas to an incorrect baseline, producing cell parameters that don't match Stage A final state (0.32% mismatch).

**Spec Violation:**
docs/spec-db-workflow.md:62-65 requires:
> Stage C (Detector):
>   - Trainable: Per-panel translation along detector normal (distance offsets).
>   - Fixed: Crystal, scale, Fhkl.

Stage C should use Stage A's **final** crystal parameters (frozen), not recompute from baseline.

**Approved Fix (Path A):**

1. **Capture Stage A final cell parameters** (after Stage A LBFGS completes, ~line 4700):
   ```python
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

2. **Pass to Stage C closure** (via param_values_c dict, ~line 4862):
   ```python
   param_values_c['stage_a_final_cell'] = stage_a_final_cell
   ```

3. **Modify Stage C closure** to use frozen values (lines 3083-3091):
   ```python
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
       # Fallback: recompute (backward compatibility)
       cell_params = crystal.get_unit_cell().parameters()
       perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
       # ... (existing code)
   ```

**Rationale:**
- Eliminates dependency on `crystal` object state
- Stage C uses explicit frozen scalar values from Stage A final state
- Fallback preserves backward compatibility if needed
- Scalars extracted with `.item()` to avoid autograd graph retention

**Validation:**
- Run test_stage_c_detector_microslip
- Expected: Test PASSES (chi² gap <0.1%)
- If PASSES → Phase D COMPLETE
- If FAILS → Path B instrumentation (log Stage A final vs Stage C initial params)

**Decision Paths:**
- **Path A (Test PASSES, chi² gap <0.1%):** Fix SUCCESS → Phase D COMPLETE, mark implementation.md, commit
- **Path B (Test FAILS, chi² gap >0.1%):** Fix INCOMPLETE → investigate parameter capture logic, check max_angle_delta scope
- **Path C (Test FAILS, different error):** New blocker → return to Galph with diagnostics
- **Path D (Compilation/import error):** Code bug → fix syntax, re-run

**Estimated Effort:** 1 loop (~1-1.5 hours)

**Confidence:** HIGH (~90%) fix will resolve mismatch based on:
1. Solid root cause analysis (95% confidence from Ralph)
2. Straightforward implementation (24 lines total: 8 capture + 1 pass + 15 modify)
3. Clear validation criterion (test assertion tolerance 0.1%)
4. Low risk (fallback preserves existing behavior)

**Findings Applied:**
- PHYSICS-LOSS-003 (variance-weighted chi² consistency)
- REFINE-009 (Stage C baseline detector seeding)
- POLICY-001 (Environment Freeze, dbex-only changes)
- spec-db-workflow.md:62-65 (Stage C normative spec)

**Code Locations:**
- Stage A completion: dbex/nanobrag_refinement.py:~4700 (insertion point for capture)
- param_values_c dict: dbex/nanobrag_refinement.py:~4862 (add stage_a_final_cell key)
- Stage C closure: dbex/nanobrag_refinement.py:3083-3091 (modify cell parameter reconstruction)
- Test assertion: tests/dbex/test_torch_refine_smoke.py:1032 (chi² tolerance check)

**Dwell Status:**
- Last loop (i=251): Ralph gathering_evidence (root cause identification)
- This loop (i=252): Galph planning (fix specification)
- Dwell=0 for planning state (first planning loop)
- Next loop (i=253): MUST be ready_for_implementation per implementation floor rule

**Roadmap Alignment:**
- PERF-WARM-SIM-001 Tier 3 (Feature Completeness)
- Highest priority after Tier 2 completion (ARCH-REFINE-FLOW-001, TORCH-API-ALIGN-001 done)
- Phase D completion unblocks remaining Tier 3 initiatives

**Next Actions for Ralph (Loop i=253):**
1. Read prior analysis (stage_c_chi2_investigation.md)
2. Capture Stage A final cell params (~line 4700)
3. Pass dict to param_values_c (~line 4862)
4. Modify Stage C closure (lines 3083-3091)
5. Run test_stage_c_detector_microslip
6. Decision synthesis (4-path template)
7. Update implementation.md (mark Phase D complete)
8. Write summary.md with Turn Summary
9. Commit and push

**References:**
- plans/active/PERF-WARM-SIM-001/reports/2025-11-24T055458Z/stage_c_chi2_investigation.md (Ralph's root cause analysis)
- docs/spec-db-workflow.md:62-65 (Stage C normative spec)
- docs/findings.md:PHYSICS-LOSS-003, REFINE-009 (findings applied)

---

## Previous Evidence Summary (Loop i=251, Ralph)

Ralph investigated Stage C chi-squared mismatch and identified root cause with 95% confidence:
- Stage C applies Stage A refined parameter deltas to baseline crystal object
- Baseline may have been mutated during Stage A or differs from initialization baseline
- Result: 0.32% chi² gap (3.2× beyond 0.1% tolerance)
- Recommended Path A fix: explicit frozen values from Stage A final state
- Evidence artifacts: stage_c_chi2_investigation.md (6-section comprehensive analysis)
