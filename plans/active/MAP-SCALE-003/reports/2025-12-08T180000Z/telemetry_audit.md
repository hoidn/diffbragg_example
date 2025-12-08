# Telemetry Audit: Current Diagnostics Emission

**Phase A1 — MAP-SCALE-003**
**Date:** 2025-12-08
**Source File:** `dbex/io/writer.py:41-440`

---

## Current `/torch_diagnostics` Schema

The `write_torch_outputs()` function at `dbex/io/writer.py:41` creates the `/torch_diagnostics` HDF5 group with the following attributes and datasets:

### Top-Level Attributes (lines 181-200)

| Attribute | Type | Description | Source |
|-----------|------|-------------|--------|
| `masked_mse` | float | Masked mean squared error | `masked_mse` parameter |
| `loss_mask_coverage` | float | Fraction of pixels in loss mask | `inputs.loss_mask.mean()` |
| `n_rois` | int | Number of ROI bboxes | `len(inputs.panel_slices)` |
| `target_shape` | str | Shape of target tensor | `str(inputs.target.shape)` |
| `backend` | str | Always "nanobrag" | Hardcoded |
| `sigma_readout_provenance` | str | Source of sigma_readout | Parameter (optional) |
| `sigma_readout_reference_value` | float | Reference sigma value | Parameter (optional) |
| `roi_scoring_method` | str | Always "nelder_mead" | Hardcoded (line 193) |
| `roi_checker` | str | "score_trainer.roi_check.roiCheck" | Hardcoded (line 194) |

### Structure-Factor Telemetry (SCALE-003, lines 196-200)

| Attribute | Type | Description | Source |
|-----------|------|-------------|--------|
| `hkl_source` | str | "refined" or "raw" | `hkl_telemetry["hkl_source"]` |
| `hkl_n_reflections` | int | Number of reflections | `hkl_telemetry["hkl_n_reflections"]` |
| `hkl_mean_amplitude` | float | Mean |F| value | `hkl_telemetry["hkl_mean_amplitude"]` |
| `hkl_path` | str | Path to MTZ file | `hkl_telemetry["hkl_path"]` |

### Per-Stage Telemetry Groups (lines 263-376)

For each refinement stage (A, B, C when enabled), a subgroup `/torch_diagnostics/stage_{label}` is created containing:

- **Loss Traces:** `refine_loss_trace_sample`, `refine_loss_trace_full` (datasets)
- **Chi-squared Traces:** `chi_squared_trace_sample`, `chi_squared_trace_full` (datasets)
- **Masked-MSE Traces:** `masked_mse_trace_sample`, `masked_mse_trace_full` (datasets)
- **Best Values:** `*_best` (attrs with iteration numbers)
- **Optimizer Config:** `refine_optimizer`, `refine_stage`, `refine_history_size`, etc.
- **Variance-floor Stats:** `variance_floor_value`, `variance_floor_clamp_fraction`
- **Canonical Metrics:** `canonical_stage_label`, `canonical_chi_squared`, `canonical_roi_count`
- **Detector Distances:** `canonical_detector_distances_mm` (dataset)
- **Stage B Baseline (when Stage B):** `stage_b_baseline_rel_diff`, `stage_b_baseline_abs_diff`

---

## Structure-Factor Provenance: ALREADY PRESENT

**Finding:** Structure-factor telemetry IS currently emitted under `/torch_diagnostics`.

At `dbex/io/writer.py:196-200`:
```python
# Structure-factor telemetry (SCALE-003: track refined vs raw MTZ)
diag.attrs["hkl_source"] = hkl_telemetry["hkl_source"]
diag.attrs["hkl_n_reflections"] = int(hkl_telemetry["hkl_n_reflections"])
diag.attrs["hkl_mean_amplitude"] = float(hkl_telemetry["hkl_mean_amplitude"])
diag.attrs["hkl_path"] = str(hkl_telemetry["hkl_path"])
```

The `hkl_telemetry` dict is populated in `dbex/refine_one.py:646-651`:
```python
hkl_telemetry = {
    "hkl_source": hkl_source,
    "hkl_n_reflections": len(hkl_indices),
    "hkl_mean_amplitude": float(hkl_amp_array.mean()),
    "hkl_path": hkl_path if hkl_path else ""
}
```

---

## Gap Analysis

| Telemetry Field | Status | Location | Notes |
|-----------------|--------|----------|-------|
| `hkl_source` | **PRESENT** | writer.py:197 | "refined" or "raw" |
| `hkl_n_reflections` | **PRESENT** | writer.py:198 | Reflection count |
| `hkl_mean_amplitude` | **PRESENT** | writer.py:199 | Mean |F| |
| `hkl_path` | **PRESENT** | writer.py:200 | MTZ path |

**Conclusion:** No gap exists. The structure-factor provenance telemetry described in SCALE-003 is fully implemented and emitted to `/torch_diagnostics` attributes.

---

## Data Flow Validation

1. **CLI Entry:** `dbex/refine_one.py:386-407` — Loads refined or raw MTZ
2. **hkl_source Assignment:** Lines 384, 389, 405-406 — Sets "refined" or "raw"
3. **hkl_telemetry Construction:** Lines 646-651 — Builds telemetry dict
4. **Writer Invocation:** Lines 691-704 — Passes `hkl_telemetry` to `write_torch_outputs()`
5. **HDF5 Emission:** writer.py:196-200 — Writes to `/torch_diagnostics` attrs

---

## Recommendations

1. **No Implementation Required:** The telemetry is already present and functional.
2. **Test Coverage:** Tests at `test_refine_one_cli.py:894-898, 1421-1424` validate the telemetry.
3. **Downstream Consumers:** `test_mapping_consistency.py:494-514` validates telemetry at acceptance.

---

## References

- `dbex/io/writer.py:196-200` — Telemetry emission
- `dbex/refine_one.py:646-651` — Telemetry dict construction
- `dbex/refine_one.py:386-407` — Refined MTZ loading
- `docs/spec-db-tracing.md` §2 — Torch diagnostics expectations
- Finding SCALE-003 — Structure factor provenance
