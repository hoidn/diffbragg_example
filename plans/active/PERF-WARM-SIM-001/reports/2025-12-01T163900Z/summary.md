# PERF-WARM-SIM-001 Phase D.4 — Supervisor Analysis (2025-12-01T16:39Z)

## Failure recap
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full` regressed with `Stage C chi-squared regressed (>0.05% increase)` immediately after ARCH-REFINE-001 Phase E.2 landed; see plans/active/PERF-WARM-SIM-001/reports/2025-12-01T171800Z/pytest_stage_c_full.log.
- Small-detector telemetry in plans/active/ARCH-REFINE-001/reports/2025-12-01T161600Z/telemetry_stage_bc_small.json already shows Stage C offsets collapsing to 1.5e-8 mm while chi² still increases by 0.063%, proving the detector math is fine but the gate is reading inconsistent populations.

## Root cause
- Stage A now forces panel-mode canonical baselines whenever Stage B or Stage C runs (REFINE-FLOW-001), yet Stage C ROI-mode evaluations continue to read only the ROI subset—even when `is_full=True`—so the REFINE-007 guard compares Stage A panel χ² (210.7 M) to Stage C ROI-only χ² (210.8 M) and flags a +0.0664% regression despite detector offsets shrinking 99.99999%.
- Logged REFINE-011 in docs/findings.md to capture this mismatch; the failure is a telemetry/validation-domain bug, not a physics regression.

## Plan
1. Tag Stage A telemetry/perf counters with `validation_scope="panel"` when `force_panel_validation` triggers so downstream stages/tests know the canonical domain.
2. Thread that flag through Stage C (`stage_c_context` + telemetry) and allow `_build_stage_c_lbfgs_closure` / `_run_stage_c_lbfgs` to bypass ROI slices whenever a full validation needs to match Stage A’s panel scope.
3. Re-run the Stage C detector microslip smoketest for both detector sizes with telemetry captured under plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/ to prove chi² regression ≤0.05% on the canonical detector while offsets still shrink ≥80%.
### Turn Summary
Captured the Stage C chi² regression root cause (ROI vs panel mismatch) and logged REFINE-011 so the ledger references the failure evidence.
Refreshed docs/fix_plan.md and input.md with the plan to propagate Stage A’s validation scope into Stage C and rerun the small/full smokes under plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/.
Next step: implement the Stage A/Stage C telemetry changes and rerun both Stage C smoketests while archiving telemetry in the new artifact directory.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/ (summary.md)
