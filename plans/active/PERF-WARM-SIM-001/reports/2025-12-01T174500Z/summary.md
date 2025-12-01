# PERF-WARM-SIM-001 Loop 2025-12-01T174500Z

## Objective
Restore Stage C ROI-mode closures while keeping panel validations explicit so telemetry correctly reports both closure mode and validation scope independently, per spec-db-workflow.md:127 (ROI minibatching permitted in closures with periodic panel validations).

## Implementation
1. **dbex/refinement/stage_c_impl.py**:
   - Removed `and not force_panel_validation` guard from `stage_c_roi_mode_active` computation (line 192)
   - Added separate `validation_scope` field: `"panel"` when `force_panel_validation` is true, else `stage_c_roi_mode_label`
   - Updated `roi_mode_reason` provenance logic to reflect that ROI closures can coexist with panel validations
   - Threaded `validation_scope` through perf_counters telemetry (lines 268, 902)

2. **tests/dbex/test_torch_refine_smoke.py**:
   - Updated `test_stage_c_detector_microslip` assertions (lines 1199-1213)
   - Now checks `roi_mode` (closure mode) and `validation_scope` (validation mode) independently
   - `roi_mode` follows Stage A's ROI decision (not forced to panel just because Stage C runs)
   - `validation_scope` MUST be "panel" when Stage B/C enabled (REFINE-011)

## Test Results
### Small Detector (29 ROIs, 1 panel)
- Status: **PASSED** ✓
- roi_mode: panel (as expected, ROI count ≤ threshold)
- validation_scope: panel
- cache_mode: warm
- Offset reduction: 99.999994%
- χ² change: -0.063% (regression, but expected for small detector)

### Full Detector (92 ROIs, 60 panels)
- Status: **FAILED** ✗ (REFINE-007 chi² gate: +0.067% > 0.05% threshold)
- roi_mode: roi (✓ ROI closures restored!)
- validation_scope: panel (✓ Panel validations active!)
- cache_mode: warm
- Offset reduction: 99.999994%
- χ² change: -0.067% (regression)
- Stage A final: 2.1071e+08
- Stage C final: 2.1085e+08

## Key Findings
1. **Implementation Success**: ROI closures are now active for full detector (`roi_mode="roi"`), and `validation_scope="panel"` correctly tracks that full validations use panel mode
2. **Telemetry Alignment**: Both `roi_mode` and `validation_scope` are independently tracked in perf_counters, proving spec compliance
3. **χ² Regression Persists**: +0.067% regression is reproducible across multiple loops (2025-12-01T163900Z, 2025-12-01T170326Z, 2025-12-01T173200Z, 2025-12-01T174500Z)
4. **ROI Sampling Observation**: Stage C always samples all panels (`roi_count_sampled==roi_count_total`); `roi_sample_fraction` config only applies to Stage A

## Blocker / Decision Point
The +0.067% chi² regression is **not caused by the ROI/validation alignment** - it persists even with correct ROI closures and panel validations. This suggests either:
1. Panel-mode validation regime introduces slight numerical convergence differences for 60-panel configuration
2. LBFGS hyperparameters (tolerance_change, max_distance_delta_mm) need adjustment

**Supervisor decision required**:
- **Option A**: Relax REFINE-007 gate from ≤0.05% to ≤0.10% with architectural rationale (panel-mode validation convergence offset)
- **Option B**: Investigate Stage C LBFGS hyperparameters for 60-panel regime
- **Option C**: Accept +0.067% as spec-conformant behavior and update gate with documented exception

## Artifacts
- `collect_stage_c_small.log`: test collection log (small detector)
- `pytest_stage_c_small.log`: test execution log (small detector)
- `telemetry_stage_c_small.json`: Stage C telemetry (small detector)
- `collect_stage_c_full.log`: test collection log (full detector)
- `pytest_stage_c_full.log`: test execution log (full detector)
- `telemetry_stage_c_full.json`: Stage C telemetry (full detector)
- `stage_c_warm_cache_report.json`: Warm cache summary report
- `summarize_output.txt`: Summarize script output

## Next Actions
1. Supervisor review: Assess whether +0.067% regression is acceptable for correct SPEC-conformant behavior
2. If accepted: Relax REFINE-007 gate and rerun full smoke
3. If not accepted: Investigate LBFGS hyperparameters or diagnostic deeper dive into convergence pattern
