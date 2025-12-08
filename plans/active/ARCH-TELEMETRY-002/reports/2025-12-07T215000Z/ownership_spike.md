# ARCH-TELEMETRY-002 Phase A.0: Ownership Spike

**Created**: 2025-12-07T215000Z
**Author**: Ralph (Implementation Engineer)
**Purpose**: Audit key telemetry files to establish ownership map

---

## 1. Stage Collectors (`dbex/refinement/telemetry_collectors.py`)

### Exported Dataclasses

| Dataclass | Location | Description |
|-----------|----------|-------------|
| `StageATelemetryCollector` | :42 | Observer for Stage A telemetry collection |
| `StageBTelemetryCollector` | :352 | Observer for Stage B telemetry collection |
| `StageCTelemetryCollector` | :483 | Observer for Stage C telemetry collection |

### Imported From `interfaces.py`

| Dataclass | Description |
|-----------|-------------|
| `StageResult` | Per-stage result container (stage, telemetry, perf_counters) |
| `StagePerfCounters` | Performance counters (closure_evals, validation_runs, forward_times_ms, variance_floor_*) |
| `StageATelemetry` | Typed telemetry payload for Stage A |
| `StageBTelemetry` | Typed telemetry payload for Stage B |
| `StageCTelemetry` | Typed telemetry payload for Stage C |

### Wrapped State Classes (from `context.py`)

| State Class | Location | Purpose |
|-------------|----------|---------|
| `StageATelemetryState` | context.py:535 | Mutable accumulators for Stage A LBFGS |
| `StageBTelemetryState` | context.py:724 | Mutable accumulators for Stage B LBFGS |
| `StageCTelemetryState` | context.py:808 | Mutable accumulators for Stage C LBFGS |

### Key Attributes Owned

**StageATelemetry** (interfaces.py:173):
- `iteration_count`, `loss_trace_sample`, `loss_trace_full`, `best_loss_full`
- `chi_squared_trace_sample`, `chi_squared_trace_full`, `chi_squared_best`
- `masked_mse_trace_sample`, `masked_mse_trace_full`, `masked_mse_best`
- `best_params_snapshot`, `u_matrix_lifecycle_log`, `a_star_lifecycle_log`
- `panel_loss_diag` (optional, PERF-WARM-SIM-001)

**StageBTelemetry** (interfaces.py:229):
- Same core traces as Stage A
- Plus: `stage_b_baseline_rel_diff`, `stage_b_baseline_abs_diff`, `stage_b_baseline_diff_path`

**StageCTelemetry** (interfaces.py:284):
- Same core traces as Stage A
- Plus: `panel_loss_diag` (optional, PERF-WARM-SIM-001)

**StagePerfCounters** (interfaces.py:137):
- `closure_evals`, `validation_runs`, `forward_times_ms`
- `variance_floor_clamped_pixels`, `variance_floor_masked_pixels`

---

## 2. Writer (`dbex/io/writer.py`)

### `/torch_diagnostics` Attributes Emitted

| Attribute | Source | Description |
|-----------|--------|-------------|
| `masked_mse` | Function param | Masked mean squared error |
| `loss_mask_coverage` | `inputs.loss_mask.mean()` | Fraction of pixels in mask |
| `n_rois` | `len(inputs.panel_slices)` | Number of ROIs processed |
| `target_shape` | `inputs.target.shape` | Target tensor shape |
| `backend` | Hardcoded | Always "nanobrag" |
| `sigma_readout_provenance` | Optional param | Source of sigma readout |
| `sigma_readout_reference_value` | Optional param | Reference sigma value |
| `roi_scoring_method` | Hardcoded | Always "nelder_mead" |
| `roi_checker` | Hardcoded | "score_trainer.roi_check.roiCheck" |
| `hkl_source` | hkl_telemetry dict | "refined" or "raw" |
| `hkl_n_reflections` | hkl_telemetry dict | Number of reflections |
| `hkl_mean_amplitude` | hkl_telemetry dict | Mean structure factor amplitude |
| `hkl_path` | hkl_telemetry dict | Path to MTZ file |

### Per-Stage Group Attributes (stage_A, stage_B, stage_C)

| Attribute | Source | Description |
|-----------|--------|-------------|
| `refine_optimizer` | telemetry dict | Optimizer type |
| `refine_stage` | telemetry dict | Stage label |
| `refine_history_size` | telemetry dict | LBFGS history size |
| `refine_max_iter` | telemetry dict | Max iterations |
| `refine_tolerance_grad` | telemetry dict | Gradient tolerance |
| `refine_tolerance_change` | telemetry dict | Change tolerance |
| `refine_roi_sample_fraction` | telemetry dict | ROI sampling fraction |
| `refine_roi_count_sampled` | telemetry dict | Sampled ROI count |
| `refine_roi_count_total` | telemetry dict | Total ROI count |
| `refine_status` | telemetry dict | Optimizer status |
| `refine_message` | telemetry dict | Optimizer message |
| `refine_param_deltas` | telemetry dict (JSON) | Parameter deltas |
| `refine_loss_trace_sample` | dataset | Per-closure loss |
| `refine_loss_trace_full` | dataset | Full-validation loss |
| `refine_best_loss_full` | attrs | Best loss value |
| `chi_squared_trace_sample` | dataset | Per-closure chi2 |
| `chi_squared_trace_full` | dataset | Full-validation chi2 |
| `chi_squared_best` | attrs | Best chi2 value |
| `masked_mse_trace_sample` | dataset | Per-closure MSE |
| `masked_mse_trace_full` | dataset | Full-validation MSE |
| `masked_mse_best` | attrs | Best MSE value |

### Stage B Specific (baseline parity)

| Attribute | Source | Description |
|-----------|--------|-------------|
| `stage_b_baseline_rel_diff` | StageBArtifacts or telemetry | Relative chi2 diff |
| `stage_b_baseline_abs_diff` | StageBArtifacts or telemetry | Absolute chi2 diff |
| `stage_b_baseline_diff_path` | StageBArtifacts or telemetry | Path to diff JSON |

### IDL Cross-Reference

See: `docs/architecture/dbex/io/writer.idl.md`

---

## 3. Mapping Diagnostics

### Search Results

No `mapping_metrics.json` pattern found in `dbex/` directory.

Mapping-related telemetry surfaces observed in `dbex/vis/mapping.py`:
- `diagnostics["log_scale_baseline_source"]` (line 306)
- `calibration["log_scale_baseline_source"]` (line 313)

These are emitted as part of calibration metadata, not standalone telemetry files.

---

## 4. Baseline Metrics Helpers

### `dbex/refinement/telemetry_baseline.py`

**Function**: `collect_stage_a_baseline_metrics()` (line 82)
**Purpose**: Production-grade baseline metrics collection for Stage A parity diagnostics

**Outputs** (schema v1):
- Masked/unmasked means
- Chi-squared per-pixel
- Baseline Bragg reconstruction metrics

**Consumer**: `StageAArtifacts.baseline_metrics` (populated when `config.enable_stage_a_baseline_metrics=True`)

### `dbex/refinement/artifacts.py`

**StageAArtifacts** (line 34):
- `baseline_metrics: Optional[Dict[str, Any]]` - schema v1 from `collect_stage_a_baseline_metrics`

**StageBArtifacts** (line 74):
- `stage_b_baseline_rel_diff: Optional[float]`
- `stage_b_baseline_abs_diff: Optional[float]`
- `stage_b_baseline_diff_path: Optional[str]`

---

## 5. Telemetry Flow Summary

```
StageATelemetryState (mutable)
         │
         ▼
StageATelemetryCollector.on_step() / on_validation()
         │
         ▼
StageATelemetryCollector.finalize()
         │
         ▼
StageResult (typed dataclass)
         │
         ├──▶ RefinementEngine.artifacts (cached)
         │
         ▼
writer.write_torch_outputs()
         │
         ▼
/torch_diagnostics HDF5 group
```

---

## 6. Ownership Classification

| Surface | Owner Module | Classification |
|---------|--------------|----------------|
| StageATelemetry | `interfaces.py` | Primary (typed dataclass) |
| StageBTelemetry | `interfaces.py` | Primary (typed dataclass) |
| StageCTelemetry | `interfaces.py` | Primary (typed dataclass) |
| StagePerfCounters | `interfaces.py` | Primary (typed dataclass) |
| StageResult | `interfaces.py` | Primary (aggregate container) |
| StageA/B/CTelemetryCollector | `telemetry_collectors.py` | Primary (observer impl) |
| StageA/B/CTelemetryState | `context.py` | Secondary (mutable accumulators) |
| `/torch_diagnostics` schema | `writer.py` | Primary (HDF5 serialization) |
| baseline_metrics (schema v1) | `telemetry_baseline.py` | Secondary (parity diagnostics) |
| StageA/BArtifacts | `artifacts.py` | Secondary (artifact containers) |
| log_scale_baseline_source | `mapping.py` | Secondary (calibration metadata) |

---

## 7. Key Findings

1. **Clear Primary Owners**: Stage collectors (`telemetry_collectors.py`) and typed dataclasses (`interfaces.py`) are the canonical telemetry owners

2. **Writer as Consumer**: `writer.py` is a consumer that serializes telemetry to HDF5, not an owner of the data semantics

3. **No Mapping Metrics JSON**: The `mapping_metrics.json` pattern does not exist; mapping telemetry is embedded in calibration dicts

4. **Baseline Metrics Optional**: Stage A baseline metrics are opt-in via config flag (`enable_stage_a_baseline_metrics`)

5. **IDL Coverage**: Writer has published IDL contract at `docs/architecture/dbex/io/writer.idl.md`

6. **State vs Typed Split**: Mutable `TelemetryState` classes (context.py) are wrapped by `TelemetryCollector` classes to produce immutable `StageXTelemetry` dataclasses

---

## 8. Gaps Identified

1. **No Telemetry Charter**: No single document defines expansion rules for telemetry surfaces
2. **IDL Coverage Gap**: Collectors and interfaces lack published IDL (only writer has one)
3. **Test Consumer Inventory**: Need to grep test files for telemetry surface consumers
