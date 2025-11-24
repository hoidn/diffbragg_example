### Turn Summary
Stage C chi-squared mismatch root cause identified with 95% confidence: Stage C recomputes cell parameters from potentially-mutated baseline crystal instead of using Stage A frozen final values.
Investigation pinpointed that Stage C applies Stage A refined parameter deltas to crystal.get_unit_cell().parameters(), which may not match the baseline used during Stage A initialization, causing 0.32% chi-squared gap (3.2× beyond 0.1% tolerance).
Next: Implement explicit Stage A final cell parameter capture and pass frozen values to Stage C, eliminating crystal object state dependency.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-24T055458Z/ (stage_c_chi2_investigation.md)

---

## Investigation Summary

**Problem:** test_stage_c_detector_microslip fails with chi-squared assertion error
- Stage C initial chi²: 2.918e+08
- Stage A final chi²: 2.909e+08
- Gap: 0.94e+06 (0.32% relative)
- Tolerance: ±0.1% (rel=1e-3)
- Result: FAIL (3.2× beyond tolerance)

**Root Cause (95% confidence):**

Stage C closure receives Stage A's refined parameter tensors (`log_cell_a_delta`, `log_cell_b_delta`, etc.) but recomputes cell parameters from the baseline `crystal` object:

```python
# dbex/nanobrag_refinement.py:3083-3084
cell_params = crystal.get_unit_cell().parameters()  # ← baseline crystal
perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)  # ← applies Stage A refined delta
```

**The issue:** The `crystal` object passed to Stage C (line 4947) may have been mutated during Stage A, or its unit cell parameters don't exactly match the baseline used during Stage A initialization. This causes Stage C to apply refined deltas to an incorrect baseline, producing cell parameters that don't match Stage A's final state.

**Spec violation:** docs/spec-db-workflow.md:62-65 states:
> Stage C (Detector):
>   - Trainable: Per-panel translation along detector normal (distance offsets).
>   - Fixed: Crystal, scale, Fhkl.

Stage C should use Stage A's **final** crystal parameters (frozen), not recompute from baseline.

**Evidence:**
1. Parameter tensors ARE frozen correctly (lines 2885-2887 in _build_stage_c_params)
2. Parameter reconstruction formulas ARE identical between Stage A and Stage C
3. BUT: `crystal.get_unit_cell().parameters()` may return different values in Stage C vs Stage A initialization
4. Chi² mismatch (0.32%) is consistent with small cell parameter errors (~0.1-0.3%) propagating through reciprocal-space calculations

**Recommended Fix (Path A):**

1. After Stage A completes, explicitly compute and capture final cell parameters:
   ```python
   with torch.no_grad():
       stage_a_final_cell = {
           'cell_a': cell_params[0] * torch.exp(log_cell_a_delta).item(),
           'cell_b': cell_params[1] * torch.exp(log_cell_b_delta).item(),
           'cell_c': cell_params[2] * torch.exp(log_cell_c_delta).item(),
           'alpha': cell_params[3] + (torch.tanh(angle_alpha_raw) * 10.0).item(),
           'beta': cell_params[4] + (torch.tanh(angle_beta_raw) * 10.0).item(),
           'gamma': cell_params[5] + (torch.tanh(angle_gamma_raw) * 10.0).item(),
       }
   ```

2. Pass `stage_a_final_cell` dict to Stage C closure

3. In Stage C closure, use frozen values directly:
   ```python
   perturbed_cell_a = stage_a_final_cell['cell_a']  # no recomputation
   perturbed_cell_b = stage_a_final_cell['cell_b']
   # ...
   ```

4. Validate with test_stage_c_detector_microslip; chi² gap should be <0.1%

**Estimated effort:** 1 loop (implementation + validation)

**Alternative (Path B - if Path A fails):**
Instrument both stages to log baseline crystal unit cell at Stage A start, Stage A end, and Stage C start to identify where crystal object is mutated. Estimated effort: 1-2 loops.

## Code Locations

**Stage C closure cell parameter reconstruction:**
- `dbex/nanobrag_refinement.py:3083-3091` (compute_loss_stage_c)

**Stage C closure construction:**
- `dbex/nanobrag_refinement.py:2985-3001` (_build_stage_c_lbfgs_closure signature)
- `dbex/nanobrag_refinement.py:4936-4952` (_build_stage_c_lbfgs_closure call)
- `dbex/nanobrag_refinement.py:4862-4879` (param_values_c dict)
- `dbex/nanobrag_refinement.py:4947` (crystal parameter passed to closure)

**Stage C parameter freezing:**
- `dbex/nanobrag_refinement.py:2885-2887` (_build_stage_c_params)

**Test assertion:**
- `tests/dbex/test_torch_refine_smoke.py:1030-1034` (chi² assertion)

## Hypothesis Ranking

1. **H1 (LIKELY, ~60%):** `crystal` object state divergence
   - Crystal object mutated during Stage A
   - Stage C applies deltas to mutated baseline
   - Fix: Pass explicit frozen values

2. **H2 (LIKELY, ~35%):** Floating-point accumulation in parameter reconstruction
   - Numerical precision differences
   - Fix: Verify identical reconstruction formulas (already done: formulas ARE identical)

3. **H3 (POSSIBLE, ~4%):** HKL grid device/dtype mismatch
   - Would cause large chi² jump (10-100×), not 0.32%
   - Verdict: UNLIKELY

4. **H4 (UNLIKELY, ~1%):** Telemetry chi² extraction bug
   - Telemetry routing verified
   - Verdict: REJECTED

## Next Steps for Implementation Loop

1. **Location:** `dbex/nanobrag_refinement.py:4700-4800` (after Stage A completes, before Stage C initialization)
2. **Compute Stage A final cell params** (with torch.no_grad())
3. **Pass dict to Stage C** via `param_values_c` (add key `'stage_a_final_cell'`)
4. **Modify Stage C closure** (lines 3083-3091) to use frozen values instead of recomputing
5. **Run test:** `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip -v`
6. **Validate:** Chi² gap <0.1% (assertion passes)
7. **Commit:** "PERF-WARM-SIM-001 Phase D: Fix Stage C chi-squared initialization (freeze Stage A final cell params)"

## Findings Applied

- PHYSICS-LOSS-003 (variance-weighted chi² consistency)
- REFINE-009 (Stage C baseline detector seeding)
- POLICY-001 (Environment Freeze, evidence-only)
- spec-db-workflow.md:62-65 (Stage C normative spec)

## Artifacts

- `plans/active/PERF-WARM-SIM-001/reports/2025-11-24T055458Z/stage_c_chi2_investigation.md` (comprehensive 6-section root cause analysis)
- This summary

## References

- `input.md` (supervisor handoff, evidence-only investigation)
- `docs/spec-db-workflow.md:62-65` (Stage C spec: Fixed crystal/scale/Fhkl)
- `plans/active/PERF-WARM-SIM-001/implementation.md` (Phase D context)
- `plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/summary.md` (prior blocker resolution)

---

### Previous Turn Summary (Galph Planning)
Completed Tier 2 (ARCH-REFINE-FLOW-001, TORCH-API-ALIGN-001), selected PERF-WARM-SIM-001 Phase D as highest priority Tier 3 focus per Execution Roadmap.
Phase D D1-D3 code complete (detector reuse implementation), telemetry routing unblocked (commit 5be669c), but NEW blocker: Stage C initial chi² (2.918e+08) exceeds Stage A final (2.909e+08) by 0.32% (tolerance 0.1%).
Next: Ralph investigates root cause via evidence gathering (hypothesis: Stage C missing Stage A cell refinement deltas); if confirmed, targeted 1-loop fix applies Stage A final params to Stage C initialization.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-24T055458Z/ (focus_selection_decision.md, input.md)
