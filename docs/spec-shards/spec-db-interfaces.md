# spec-db-interfaces.md — Interface Specification (Normative)

<!--
Bootstrap iteration 4: Extracted from:
- dbex/refine_one.py (CLI parser, backend dispatch, sigma resolution)
- dbex/io/writer.py (HDF5 output schema, torch_diagnostics group)
- docs/index.md (usage examples)
-->

---

## Overview (Normative)

- **Purpose:** Define CLI and API interfaces for diffBragg refinement.
- **Scope:** Command-line interface, programmatic API, parameter handling, output formats.
- **Status:** Active. All implementations MUST conform.

---

## Command-Line Interface (Normative)

### Primary Command

| Command | Purpose | Module |
|---------|---------|--------|
| `python -m dbex.refine_one` | Single-experiment refinement with backend dispatch | `dbex.refine_one` |

**Synopsis:**
```bash
python -m dbex.refine_one --backend {diffbragg|nanobrag} \
    -e EXPT_FILE -r REFL_FILE -i EXPT_IDX \
    -o OUT_FILE -m MASK_FILE -z MTZ_FILE \
    [--sigma-rdout VALUE] [--sigma-map PATH] [--sigma-floor VALUE] \
    [--adu-per-photon VALUE] [--device DEVICE] \
    [--torch-config PATH] [--refined-mtz PATH] \
    [--spot-scale-override VALUE] [--mtzCol COLS] \
    [--enable-stage-b] [--enable-stage-c] [--report-dir DIR]
```

---

### Required Arguments

| Argument | Short | Type | Contract |
|----------|-------|------|----------|
| `--exptName` | `-e` | `str` | Path to DIALS experiment list (`.json`). SHALL exist. |
| `--reflName` | `-r` | `str` | Path to DIALS reflection table (`.refl`). SHALL exist. |
| `--exptIdx` | `-i` | `int` | Experiment index (0-indexed). SHALL be in valid range. |
| `--outFile` | `-o` | `str` | Output HDF5 path. Parent directory SHOULD exist. |
| `--maskFile` | `-m` | `str` | Detector mask file path (pickle or numpy). SHALL exist. |
| `--mtzFile` | `-z` | `str` | MTZ file with structure factors. SHALL exist. |

---

### Optional Arguments

#### Backend Selection

| Argument | Type | Default | Contract |
|----------|------|---------|----------|
| `--backend` | `str` | `"diffbragg"` | SHALL be one of `["diffbragg", "nanobrag"]`. `diffbragg` uses legacy DiffBragg refinement; `nanobrag` uses PyTorch-based nanobrag_torch. |

#### Device Configuration

| Argument | Type | Default | Contract |
|----------|------|---------|----------|
| `--device` | `str` | `"cuda:0"` | PyTorch device specifier for nanobrag backend. If CUDA unavailable, SHALL fall back to CPU with warning. Invalid device SHALL raise `ValueError`. |

#### Sigma/Variance Configuration

| Argument | Type | Default | Contract |
|----------|------|---------|----------|
| `--sigma-rdout` | `float` | `None` | Detector readout noise (photons or ADU). If provided, SHALL be `> 0`. |
| `--sigma-map` | `str` | `None` | Path to calibrated sigma_readout tensor file (`.npy`, `.npz`, or pickle). |
| `--sigma-floor` | `float` | `1.0` | Variance floor guard in target units. Prevents infinite weights when I_model → 0. Per `spec-db-core.md` §Variance Model, variance is clamped: `V = max(I_model + σ_rdout², σ_floor²)`. |

#### Calibration Configuration

| Argument | Type | Default | Contract |
|----------|------|---------|----------|
| `--adu-per-photon` | `float` | `None` | ADU→photon conversion gain. If provided, SHALL be `> 0`. When set, targets are converted to photons; otherwise targets remain in ADU with learnable global scale. Per `spec-db-workflow.md` §Configuration Precedence. |
| `--spot-scale-override` | `float` | `None` | Optional spot scale for nanobrag backend. Applies `sqrt(scale)` post-simulation per SCALE-002. |
| `--torch-config` | `str` | `None` | Path to DiffBragg `config_torch.json` with calibration metadata (spot_scale_override, beam flux/exposure/beamsize, N_cells). When provided, overrides `--spot-scale-override`. Gracefully skipped if missing. |

#### Structure Factor Configuration

| Argument | Type | Default | Contract |
|----------|------|---------|----------|
| `--mtzCol` | `str` | `"F,SIGF"` | MTZ column names for structure factors and sigmas. |
| `--refined-mtz` | `str` | `None` | Path to DiffBragg-refined structure factor MTZ. When provided, SHALL use refined Fopt instead of raw MTZ. If file missing or invalid, CLI SHALL fail fast with `RuntimeError` (no silent fallback per SCALE-007). |

#### Stage Configuration

| Argument | Type | Default | Contract |
|----------|------|---------|----------|
| `--enable-stage-b` | `flag` | `False` | Enable Stage B Fhkl shell modifiers. Per `spec-db-workflow.md` §Stage B. |
| `--enable-stage-c` | `flag` | `False` | Enable Stage C detector distance refinement. Per `spec-db-workflow.md` §Stage C. |

#### Output Configuration

| Argument | Type | Default | Contract |
|----------|------|---------|----------|
| `--report-dir` | `str` | `None` | Directory for triptych report PNGs. When specified, generates `roi_NNNN_triptych.png` for all ROIs after refinement completes. Directory is created if it does not exist. |

---

### Parameter Precedence (Normative)

When a parameter can be specified via multiple sources, the following precedence SHALL apply:

```
1. CLI argument (highest precedence)
2. Calibration metadata file (--torch-config)
3. Calibrated map/external_lookup (--sigma-map, DIALS metadata)
4. Hardcoded default (lowest precedence)
```

#### Sigma Readout Resolution

Per `_resolve_sigma_readout()` in `dbex/refine_one.py`:

```
1. CLI scalar (--sigma-rdout) — Highest; broadcasts to tensor shape
2. Calibrated map (--sigma-map or external_lookup) — Per-pixel values
3. No source available — CLI SHALL abort with ValueError
```

**Error Condition:** When no sigma source is available and backend is `nanobrag`, the CLI SHALL raise `ValueError` with message listing required options: `--sigma-rdout`, `--sigma-map`, or `external_lookup` metadata.

#### Spot Scale Resolution

```
1. Calibration metadata (torch_config['spot_scale_override'])
2. CLI argument (--spot-scale-override)
3. Default: 1.0
```

#### Refined MTZ Enforcement (SCALE-007)

When `--refined-mtz` is provided:
- The CLI MUST attempt to load the refined structure factors.
- If loading fails (file not found, invalid format), the CLI SHALL raise `RuntimeError`.
- The CLI MUST NOT silently fall back to raw MTZ from `--mtzFile`.

---

### Exit Codes (Normative)

| Code | Meaning | Condition |
|------|---------|-----------|
| `0` | Success | Refinement completed, HDF5 written. |
| `1` | General error | Unhandled exception during refinement. |
| `2` | Invalid arguments | argparse validation failure (missing required args, invalid choices). |
| `3` | Missing sigma source | No `--sigma-rdout`, `--sigma-map`, or `external_lookup` available (nanobrag only). |

**Note:** Exit codes 2 and 3 are raised by Python exceptions; current implementation does not set explicit exit codes but propagates exception termination.

---

### Error Conditions (Normative)

| Condition | Behavior |
|-----------|----------|
| `--sigma-rdout <= 0` | SHALL raise `ValueError` with message "must be > 0" |
| `--sigma-rdout` absent and no calibrated map/metadata | SHALL raise `ValueError` listing required options |
| Invalid `--device` specifier | SHALL raise `ValueError` with message containing "Invalid --device" |
| CUDA requested but unavailable | SHALL fall back to CPU with warning (no error) |
| `--refined-mtz` provided but file missing | SHALL raise `RuntimeError` with message containing "Failed to load refined structure factors" |
| `--refined-mtz` provided but invalid format | SHALL raise `RuntimeError` (no silent fallback) |
| Unknown `--backend` value | SHALL raise `ValueError` with message "Unknown backend" |

---

## Output Formats (Normative)

### HDF5 Output Schema

**File:** `{outFile}` specified via `-o/--outFile`

#### Root-Level Datasets

| Dataset | Type | Shape | Contract |
|---------|------|-------|----------|
| `score` | `float64` | `[n_rois]` | Per-ROI correlation scores in `[0, 1]`. |
| `bragg_scale` | `float64` | `[n_rois]` | Per-ROI optimal Bragg scale factors (Nelder-Mead optimized). |
| `sigma_readout` | `float64` | scalar | Sigma readout reference value in target units. |
| `sigma_floor` | `float64` | scalar | Variance floor value in target units. |

#### ROI Triptych Datasets

For each ROI `i` in `[0, n_rois)`:

| Dataset | Type | Shape | Contract |
|---------|------|-------|----------|
| `data/roi{i}` | `float32` | `[slow, fast]` | Observed target intensities for ROI. |
| `model/roi{i}` | `float32` | `[slow, fast]` | Model = background + scaled Bragg. |
| `bragg/roi{i}` | `float32` | `[slow, fast]` | Simulated Bragg intensities (unscaled). |
| `bg/roi{i}` | `float32` | `[slow, fast]` | Background estimate for ROI. |
| `variance/roi{i}` | `float32` | `[slow, fast]` | Per-pixel variance per `spec-db-core.md` §Variance Model. |

---

### torch_diagnostics Group (nanobrag backend only)

**Group:** `/torch_diagnostics`

#### Root Attributes

| Attribute | Type | Contract |
|-----------|------|----------|
| `masked_mse` | `float` | Masked mean squared error between target and Bragg. |
| `loss_mask_coverage` | `float` | Fraction of pixels in loss mask (in `[0, 1]`). |
| `n_rois` | `int` | Number of ROIs processed. |
| `target_shape` | `str` | Shape of target tensor as string (e.g., `"(64, 2527, 2463)"`). |
| `backend` | `str` | SHALL be `"nanobrag"`. |
| `sigma_readout_provenance` | `str` | Source identifier: `"cli_override"`, `"calibrated_map"`, or `"external_lookup"`. |
| `sigma_readout_reference_value` | `float` | Reference sigma value in target units. |
| `roi_scoring_method` | `str` | Scoring algorithm: `"nelder_mead"`. |
| `roi_checker` | `str` | Scorer class: `"score_trainer.roi_check.roiCheck"`. |

#### Structure-Factor Telemetry Attributes

| Attribute | Type | Contract |
|-----------|------|----------|
| `hkl_source` | `str` | SHALL be `"refined"` or `"raw"`. |
| `hkl_n_reflections` | `int` | Number of structure factor reflections used. |
| `hkl_mean_amplitude` | `float` | Mean amplitude of structure factors. |
| `hkl_path` | `str` | Path to MTZ file used. |

#### Per-Stage Telemetry Groups

For each executed stage `{LABEL}` in `["A", "B", "C"]`:

**Group:** `/torch_diagnostics/stage_{LABEL}`

| Attribute/Dataset | Type | Contract |
|-------------------|------|----------|
| `refine_optimizer` | `str` (attr) | Optimizer name (`"LBFGS"` or `"Adam"`). |
| `refine_stage` | `str` (attr) | Stage label. |
| `refine_status` | `str` (attr) | Status: `"ok"`, `"early_stop"`, `"rollback"`, or `"error"`. |
| `refine_message` | `str` (attr) | Status description. |
| `refine_history_size` | `int` (attr) | LBFGS history size. |
| `refine_max_iter` | `int` (attr) | Maximum iterations. |
| `refine_tolerance_grad` | `float` (attr) | Gradient tolerance. |
| `refine_tolerance_change` | `float` (attr) | Change tolerance. |
| `refine_roi_sample_fraction` | `float` (attr) | ROI sampling fraction. |
| `refine_roi_count_sampled` | `int` (attr) | Number of ROIs sampled. |
| `refine_roi_count_total` | `int` (attr) | Total number of ROIs. |
| `refine_best_loss_full` | `float` (attr) | Best loss on full evaluation. |
| `refine_best_loss_iteration` | `int` (attr) | Iteration of best loss. |
| `chi_squared_best` | `float` (attr) | Best chi-squared value. |
| `chi_squared_best_iteration` | `int` (attr) | Iteration of best chi-squared. |
| `masked_mse_best` | `float` (attr) | Best masked MSE value. |
| `masked_mse_best_iteration` | `int` (attr) | Iteration of best masked MSE. |
| `refine_param_deltas` | `str` (attr) | JSON-encoded parameter deltas dict. |
| `refine_loss_trace_sample` | `float64[]` (dataset) | Loss per closure on sampled subset. |
| `refine_loss_trace_full` | structured array (dataset) | `[(iteration, loss), ...]` tuples. dtype: `[('iteration', 'i4'), ('loss', 'f8')]`. |
| `chi_squared_trace_sample` | `float64[]` (dataset) | Chi² per closure on sampled subset. |
| `chi_squared_trace_full` | structured array (dataset) | `[(iteration, chi_squared), ...]`. dtype: `[('iteration', 'i4'), ('chi_squared', 'f8')]`. |
| `masked_mse_trace_sample` | `float64[]` (dataset) | MSE per closure on sampled subset. |
| `masked_mse_trace_full` | structured array (dataset) | `[(iteration, masked_mse), ...]`. dtype: `[('iteration', 'i4'), ('masked_mse', 'f8')]`. |

**Stage B Additional Attributes:**

| Attribute | Type | Contract |
|-----------|------|----------|
| `stage_b_baseline_rel_diff` | `float` | Relative difference from Stage A baseline chi². |
| `stage_b_baseline_abs_diff` | `float` | Absolute difference from Stage A baseline chi². |
| `stage_b_baseline_diff_path` | `str` | Path to baseline diff artifact (if saved). |

**Stage C Additional Datasets:**

| Dataset | Type | Contract |
|---------|------|----------|
| `canonical_detector_distances_mm` | `float64[]` | Final detector panel distances in mm. |

---

## Programmatic API (Normative)

### Entry Points

| Function | Purpose | Module |
|----------|---------|--------|
| `main(argv=None)` | CLI entry point; parses args, loads data, dispatches backend | `dbex.refine_one` |
| `create_parser()` | Returns configured `ArgumentParser` | `dbex.refine_one` |
| `run_diffbragg_backend(args, DL, devid)` | Legacy DiffBragg refinement | `dbex.refine_one` |
| `run_nanobrag_backend(args, DL, devid)` | PyTorch nanobrag_torch refinement | `dbex.refine_one` |
| `write_torch_outputs(...)` | HDF5 writer with ROI scoring | `dbex.io.writer` |
| `RefinementEngine` | Protocol-based refinement engine | `dbex.refinement.engine` |
| `prepare_refinement_inputs(...)` | Prepare typed inputs for refinement | `dbex.refinement.inputs` |

---

### write_torch_outputs

**Purpose:** Write torch backend outputs to HDF5 with diagnostics.

**Signature:**
```python
write_torch_outputs(
    args,                           # CLI args namespace
    data_load,                      # DataLoad object
    bragg,                          # Simulated Bragg array [n_panels, slow, fast]
    inputs,                         # RefinementInputs namedtuple
    masked_mse,                     # Masked MSE float
    hkl_telemetry,                  # Structure-factor metadata dict
    refine_telemetry=None,          # Optional Dict[str, RefinementTelemetry]
    sigma_readout_provenance=None,  # Optional str
    sigma_readout_reference_value=None,  # Optional float
    stage_artifacts=None,           # Optional Dict[str, Any]
    roi_payloads=None,              # List[ROIAnalysisPayload] (REQUIRED)
    stage_results=None,             # Optional Dict[str, StageResult]
)
```

**Preconditions:**
1. `roi_payloads` SHALL NOT be `None`. Passing `None` SHALL raise `ValueError`.
2. Each `roi_payloads[i].model` SHALL NOT be `None`.
3. Each `roi_payloads[i].variance` SHALL NOT be `None`.

**Behavior:**
1. Create HDF5 file at `args.outFile`.
2. Write root-level datasets: `score`, `bragg_scale`, `sigma_readout`, `sigma_floor`.
3. Write per-ROI triptych datasets from `roi_payloads`.
4. Create `/torch_diagnostics` group with attributes and telemetry.
5. Serialize per-stage telemetry groups when `refine_telemetry` is provided.

**Error Conditions:**

| Condition | Behavior |
|-----------|----------|
| `roi_payloads is None` | SHALL raise `ValueError` with message "roi_payloads must be non-None" |
| `roi_payloads[i].model is None` | SHALL raise `ValueError` with index in message |
| `roi_payloads[i].variance is None` | SHALL raise `ValueError` with index in message |

---

### _resolve_sigma_readout

**Purpose:** Resolve sigma_readout source and provenance per `spec-db-core.md` §Sigma Readout Resolution.

**Signature:**
```python
_resolve_sigma_readout(args, dataload) -> Tuple[np.ndarray, str, float]
```

**Returns:**
- `sigma_array` — `np.ndarray` shaped like `dataload.data` with strictly positive values.
- `provenance` — `str` describing the source: `"cli_override"`, `"calibrated_map"`, or `"external_lookup"`.
- `reference_value` — `float` scalar (target units before any ADU→photon conversion).

**Priority Order:**
1. CLI scalar (`args.sigma_rdout`) — Broadcasts to full tensor shape.
2. Calibrated map from `dataload.sigma_readout_map` — Per-pixel values.

**Error Conditions:**

| Condition | Behavior |
|-----------|----------|
| `args.sigma_rdout <= 0` | SHALL raise `ValueError` with message "must be > 0" |
| `sigma_array.shape != dataload.data.shape` | SHALL raise `ValueError` with both shapes |
| `not np.all(sigma_array > 0)` | SHALL raise `ValueError` with message "strictly positive" |
| No sigma source available | SHALL raise `ValueError` listing options |

---

## References (Informative)

- `spec-db-core.md` — Core data types, variance model, validation rules
- `spec-db-workflow.md` — Pipeline stages, stage enabling, configuration precedence
- `spec-db-conformance.md` — Tests validating interface behavior
- `docs/architecture/dbex/io/writer.idl.md` — Full writer API contract
