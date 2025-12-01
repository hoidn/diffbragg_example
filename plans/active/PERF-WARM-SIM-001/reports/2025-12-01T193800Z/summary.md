### Turn Summary
Re-implemented REFINE-012 ROI-mode gate (`and not force_panel_validation`) in stage_c_impl.py:189-193 and added `roi_mode_reason="validation_scope_panel"` branch; small detector passed with panel mode confirmed.
Full detector reproduced identical +0.067% chi² regression (Stage A final=2.1071e+08, Stage C final=2.1085e+08) as 2025-12-01T170326Z, triggering repeat-failure guard: chi² trace flat across LBFGS iterations (all validations=210848512.0), indicating panel-mode closures may cause LBFGS stall rather than converge.
Next: Supervisor must decide—accept +0.067% as inherent to panel-mode closures, adjust LBFGS hyperparams (tolerance_change, max_iter), or investigate why panel-mode LBFGS does not improve objective function.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T193800Z/ (telemetry_stage_c_small.json, telemetry_stage_c_full.json, pytest_stage_c_small.log, pytest_stage_c_full.log, collect logs)

### Repeat-Failure Analysis
**Prior loop**: 2025-12-01T170326Z (docs/fix_plan.md:959-970)
- Implementation: Added `and not force_panel_validation` to `stage_c_roi_mode_active`
- Full detector result: chi² regression +0.067% (2.1071e+08 → 2.1085e+08)
- Status: PARTIAL SUCCESS (detector offsets converged, chi² gate failed)

**Current loop**: 2025-12-01T193800Z
- Implementation: Re-applied identical `and not force_panel_validation` condition (lines 186-194)
- Full detector result: chi² regression +0.0674% (2.1071e+08 → 2.1085e+08, identical to 4 decimal places)
- Chi² trace: Flat across all LBFGS iterations [0: 210848512.0, 5: 210848512.0, 9: 210848512.0]
- Status: **REPEAT FAILURE** per ground_rules repeat-failure guard

**Root cause hypothesis**:
Disabling ROI-mode closures forces Stage C LBFGS to evaluate the full 60-panel tensor on every closure call. The chi² trace remaining flat suggests:
1. LBFGS may be stalling due to numerical precision issues with full-panel gradients
2. Or convergence tolerances (`tolerance_change`, `tolerance_grad`) tuned for ROI minibatching may be too strict for panel-mode regime
3. Or the detector offset parameterization (`torch.tanh` bounded) may prevent LBFGS from exploring sufficient parameter space when starting from perturbed geometry

The small detector (1 panel, 29 ROIs) passes with early-stop due to negligible improvement, while the full detector (60 panels, 92 ROIs) shows zero LBFGS progress over 9 closure evaluations.

**Evidence paths**:
- telemetry_stage_c_small.json: roi_mode="panel", roi_mode_reason="validation_scope_panel", detector offsets reduced 99.999994%, chi² improved -0.0631%
- telemetry_stage_c_full.json: roi_mode="panel", roi_mode_reason="validation_scope_panel", detector offsets reduced 99.999994%, chi² regressed +0.0674% (flat trace)
- pytest_stage_c_full.log: AssertionError at line 1156, stage_c_final_chi2=2.1085e+08 > stage_a_final_chi2 * 1.0005

**Recommendation**: Mark PERF-WARM-SIM-001 Phase D.4 **blocked — suspected implementation defect (LBFGS convergence in panel mode)**. Do NOT re-run with gate adjustments until supervisor reviews whether panel-mode closures are architecturally required or if we can use an ROI-closure + panel-validation hybrid per spec-db-workflow.md:127.
