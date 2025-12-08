# ARCH-TELEMETRY-002 Phase A.2: Telemetry Inventory

**Created**: 2025-12-07T215000Z
**Author**: Ralph (Implementation Engineer)
**Purpose**: Comprehensive inventory of telemetry surfaces, owners, and consumers

---

## 1. Primary Telemetry Surfaces

### 1.1 Stage Telemetry Dataclasses

| Surface | Owner Module | Location | Fields |
|---------|--------------|----------|--------|
| `StageATelemetry` | `dbex/refinement/interfaces.py` | :173 | iteration_count, loss_trace_sample, loss_trace_full, best_loss_full, chi_squared_trace_sample, chi_squared_trace_full, chi_squared_best, masked_mse_trace_sample, masked_mse_trace_full, masked_mse_best, best_params_snapshot, u_matrix_lifecycle_log, a_star_lifecycle_log, panel_loss_diag |
| `StageBTelemetry` | `dbex/refinement/interfaces.py` | :229 | (same as A minus lifecycle logs) + stage_b_baseline_rel_diff, stage_b_baseline_abs_diff, stage_b_baseline_diff_path |
| `StageCTelemetry` | `dbex/refinement/interfaces.py` | :284 | (same as A minus lifecycle logs) + panel_loss_diag |
| `StagePerfCounters` | `dbex/refinement/interfaces.py` | :137 | closure_evals, validation_runs, forward_times_ms, variance_floor_clamped_pixels, variance_floor_masked_pixels |
| `StageResult` | `dbex/refinement/interfaces.py` | :334 | stage, telemetry (Union[StageA/B/CTelemetry]), perf_counters |

### 1.2 Telemetry Collectors

| Surface | Owner Module | Location | Wraps |
|---------|--------------|----------|-------|
| `StageATelemetryCollector` | `dbex/refinement/telemetry_collectors.py` | :42 | `StageATelemetryState` |
| `StageBTelemetryCollector` | `dbex/refinement/telemetry_collectors.py` | :352 | `StageBTelemetryState` |
| `StageCTelemetryCollector` | `dbex/refinement/telemetry_collectors.py` | :483 | `StageCTelemetryState` |

### 1.3 Telemetry State Classes (Internal)

| Surface | Owner Module | Location | Purpose |
|---------|--------------|----------|---------|
| `StageATelemetryState` | `dbex/refinement/context.py` | :535 | Mutable accumulator for Stage A LBFGS |
| `StageBTelemetryState` | `dbex/refinement/context.py` | :724 | Mutable accumulator for Stage B LBFGS |
| `StageCTelemetryState` | `dbex/refinement/context.py` | :808 | Mutable accumulator for Stage C LBFGS |

---

## 2. HDF5 `/torch_diagnostics` Schema

### 2.1 Top-Level Attributes

| Attribute | Source | Type | Description |
|-----------|--------|------|-------------|
| `masked_mse` | Function param | float | Masked mean squared error |
| `loss_mask_coverage` | `inputs.loss_mask.mean()` | float | Fraction of pixels in mask |
| `n_rois` | `len(inputs.panel_slices)` | int | Number of ROIs |
| `target_shape` | `inputs.target.shape` | str | Target tensor shape |
| `backend` | Hardcoded | str | Always "nanobrag" |
| `sigma_readout_provenance` | Optional param | str | Source of sigma readout |
| `sigma_readout_reference_value` | Optional param | float | Reference sigma value |
| `roi_scoring_method` | Hardcoded | str | "nelder_mead" |
| `roi_checker` | Hardcoded | str | "score_trainer.roi_check.roiCheck" |
| `hkl_source` | hkl_telemetry | str | "refined" or "raw" |
| `hkl_n_reflections` | hkl_telemetry | int | Reflection count |
| `hkl_mean_amplitude` | hkl_telemetry | float | Mean |F| |
| `hkl_path` | hkl_telemetry | str | MTZ path |

### 2.2 Per-Stage Groups (stage_A, stage_B, stage_C)

| Attribute/Dataset | Type | Description |
|-------------------|------|-------------|
| `refine_optimizer` | attr (str) | Optimizer type |
| `refine_stage` | attr (str) | Stage label |
| `refine_history_size` | attr (int) | LBFGS history |
| `refine_max_iter` | attr (int) | Max iterations |
| `refine_tolerance_grad` | attr (float) | Gradient tolerance |
| `refine_tolerance_change` | attr (float) | Change tolerance |
| `refine_roi_sample_fraction` | attr (float) | ROI sampling fraction |
| `refine_roi_count_sampled` | attr (int) | Sampled ROIs |
| `refine_roi_count_total` | attr (int) | Total ROIs |
| `refine_status` | attr (str) | Optimizer status |
| `refine_message` | attr (str) | Optimizer message |
| `refine_param_deltas` | attr (JSON) | Parameter deltas |
| `refine_loss_trace_sample` | dataset (float[]) | Per-closure loss |
| `refine_loss_trace_full` | dataset (structured) | (iteration, loss) tuples |
| `refine_best_loss_full` | attr (float) | Best loss |
| `refine_best_loss_iteration` | attr (int) | Best loss iteration |
| `chi_squared_trace_sample` | dataset (float[]) | Per-closure chi2 |
| `chi_squared_trace_full` | dataset (structured) | (iteration, chi2) tuples |
| `chi_squared_best` | attr (float) | Best chi2 |
| `chi_squared_best_iteration` | attr (int) | Best chi2 iteration |
| `masked_mse_trace_sample` | dataset (float[]) | Per-closure MSE |
| `masked_mse_trace_full` | dataset (structured) | (iteration, mse) tuples |
| `masked_mse_best` | attr (float) | Best MSE |
| `masked_mse_best_iteration` | attr (int) | Best MSE iteration |
| `canonical_detector_distances_mm` | dataset (float64[]) | Detector distances |

### 2.3 Stage B Specific Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `stage_b_baseline_rel_diff` | attr (float) | Relative chi2 diff A→B |
| `stage_b_baseline_abs_diff` | attr (float) | Absolute chi2 diff A→B |
| `stage_b_baseline_diff_path` | attr (str) | Path to diff JSON |

---

## 3. Secondary Telemetry Surfaces

### 3.1 Baseline Metrics (Schema v1)

| Surface | Owner Module | Location | Fields |
|---------|--------------|----------|--------|
| `collect_stage_a_baseline_metrics()` | `dbex/refinement/telemetry_baseline.py` | :82 | masked_mean, unmasked_mean, chi2_per_pixel, baseline_bragg_stats |

**Consumer**: `StageAArtifacts.baseline_metrics` (opt-in)

### 3.2 Stage Artifacts

| Surface | Owner Module | Location | Fields |
|---------|--------------|----------|--------|
| `StageAArtifacts` | `dbex/refinement/artifacts.py` | :34 | baseline_metrics |
| `StageBArtifacts` | `dbex/refinement/artifacts.py` | :74 | stage_b_baseline_rel_diff/abs_diff/diff_path |

### 3.3 Calibration Telemetry

| Surface | Owner Module | Location | Fields |
|---------|--------------|----------|--------|
| Calibration diagnostics | `dbex/vis/mapping.py` | :306 | log_scale_baseline_source |
| Stage telemetry | `dbex/refinement/stage.py` | :152 | log_scale_baseline_source |

---

## 4. Test Consumers

### 4.1 `tests/dbex/test_refine_one_cli.py`

| Test | Surfaces Consumed |
|------|------------------|
| `test_torch_diagnostics_metadata` (:913) | `/torch_diagnostics` attrs, `stage_A` group |

**Assertions**:
- `torch_diagnostics` group exists
- Required attributes present (masked_mse, loss_mask_coverage, n_rois, etc.)
- `stage_A` group present with refine_* attributes

### 4.2 `tests/dbex/test_stage_b_cpu_fallback.py`

| Test | Surfaces Consumed |
|------|------------------|
| Stage B fallback tests (:409-593) | `StageBTelemetryState`, `StageBTelemetryCollector` |

**Assertions**:
- Collector wraps state correctly
- `set_baseline_parity_metrics()` populates state
- `finalize()` returns valid `StageResult`

---

## 5. IDL Coverage

| Surface | IDL Document | Status |
|---------|--------------|--------|
| Writer `/torch_diagnostics` | `docs/architecture/dbex/io/writer.idl.md` | Complete |
| RefinementObserver protocol | `docs/architecture/dbex/refinement/interfaces.idl.md` | Complete |
| Stage telemetry dataclasses | `docs/architecture/dbex/refinement/interfaces.idl.md` | Complete |
| Telemetry collectors | None | Gap - documented in charter only |
| Baseline metrics (schema v1) | None | Gap - internal diagnostic |

---

## 6. Canonical Artifacts

| Artifact Type | Producer | Consumer |
|---------------|----------|----------|
| HDF5 `/torch_diagnostics` | `dbex/io/writer.py` | Downstream analysis, tests |
| `StageResult` dataclass | `Stage*TelemetryCollector.finalize()` | `RefinementEngine`, `writer.py` |
| `stage_artifacts` dict | `RefinementEngine` | `writer.py` |
| `baseline_metrics` JSON | `collect_stage_a_baseline_metrics()` (optional) | Parity probes |

---

## 7. Summary Statistics

| Category | Count |
|----------|-------|
| Primary telemetry dataclasses | 5 |
| Telemetry collectors | 3 |
| Mutable state classes | 3 |
| HDF5 top-level attributes | 13 |
| HDF5 per-stage attributes | ~20 |
| Secondary/diagnostic surfaces | 4 |
| Test files consuming telemetry | 2 |
| IDL documents covering telemetry | 2 |

---

## 8. Cross-References

| Document | Section |
|----------|---------|
| Telemetry Charter | `docs/architecture/telemetry.md` |
| Writer IDL | `docs/architecture/dbex/io/writer.idl.md` |
| Interfaces IDL | `docs/architecture/dbex/refinement/interfaces.idl.md` |
| Data Dependency Manifest | `docs/data_dependency_manifest.md` §Telemetry |
| Spec-DB Workflow | `docs/spec-db-workflow.md` §Calibration |
