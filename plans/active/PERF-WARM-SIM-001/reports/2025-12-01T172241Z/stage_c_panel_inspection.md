## Stage C Panel-Mode Regression Inspection (2025-12-01T172241Z)

**Scope:** PERF-WARM-SIM-001 Phase D.4 — understanding why the full-detector Stage C smoke continues to fail the ≤0.05 % χ² gate after REFINE-011/012 landed.

### Code Review Notes

1. `dbex/refinement/stage_c_impl.py:188-214` now derives `stage_c_roi_mode_active` from the Stage A telemetry flags and unconditionally disables ROI closures whenever `force_panel_validation` is set. Because Stage A always sets `validation_scope="panel"` when Stage B or Stage C are enabled (stage_a.py:210-224), the canonical detector path now evaluates *every* Stage C closure and validation on the entire 60-panel dataset.
2. `_build_stage_c_lbfgs_closure` (stage_c_impl.py:486-569) still performs ROI minibatching for gradient steps and panel-wide evaluation for `is_full` validations. After REFINE-012 the `use_roi_mode_this_eval` guard is permanently `False` for canonical runs, so both the stochastic closure and the periodic validations use the full-panel tensor stack. No remaining ROI short-circuit exists.
3. `_run_stage_c_lbfgs` (stage_c_impl.py:756-990) restores the Stage A snapshot, runs LBFGS, and reports telemetry when the optimizer terminates. There is no special-casing for the canonical detector; detector offsets are still reduced via `_retarget_stage_a_detectors`, and the per-panel offset telemetry is emitted identically to the small-detector run.
4. The strict gate inside `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (lines 1100-1205) asserts `stage_c_final_chi2 <= stage_a_final_chi2 * 1.0005` *before* `_record_stage_telemetry` is called (line 1218). When the gate fires, `DBEX_SMOKE_TELEMETRY_PATH` is never written, so we have no artifact capturing the per-iteration trace or detector offsets for the failing configuration.
5. The 2025-12-01T170326Z pytest log shows Stage A final χ² = 2.1071e+08 and Stage C final χ² = 2.1085e+08 (+0.067 %), matching the REFINE-011 loop. Detector offset checks and telemetry completeness assertions all passed prior to the gate, so the only violation is the tighter non-regression threshold that was calibrated when Stage C still used ROI-only closures.

### Conclusions

- REFINE-011 and REFINE-012 succeeded: canonical runs now execute Stage C entirely on panel-mode data so the REFINE-007 comparison is apples-to-apples. The reproducible +0.067 % regression appears to be the new steady-state when panel-mode losses are compared, not an implementation error in Stage C.
- Because `_record_stage_telemetry` is never reached when the gate fails, we lack telemetry artifacts to prove the detector-offset reduction and chi² trace behavior that would justify a gate recalibration. We need to emit telemetry before the strict asserts so future failures still produce JSON evidence.
- Next step should capture per-iteration χ² traces for the full detector and document the detector-offset reductions before changing REFINE-007. Without that evidence we cannot argue that the +0.067 % regression is acceptable or intrinsically tied to panel-mode closures.
