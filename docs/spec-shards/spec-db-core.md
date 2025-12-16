# spec-db-core.md — Core Domain Specification (Normative)

<!--
Bootstrap iteration 0: Extracted from dbex/data_load.py, dbex/refine_one.py, dbex/physics/loss.py
-->

---

## Overview (Normative)

- **Purpose:** Define fundamental domain concepts, units, and data contracts for diffBragg/nanobrag refinement.
- **Scope:** Core types, unit systems, coordinate conventions, variance model, and data validation rules.
- **Status:** Active. All implementations MUST conform.

---

## Units and Conventions (Normative)

### Unit System

| Quantity | Unit | Symbol | Notes |
|----------|------|--------|-------|
| Intensity (raw) | ADU | ADU | Analog-to-Digital Units from detector readout |
| Intensity (calibrated) | photons | ph | After ADU→photon conversion via `adu_per_photon` |
| Readout noise | ADU or photons | σ_rdout | MUST match target intensity units |
| Variance floor | ADU² or photons² | σ_floor² | Squared; MUST match target units |
| Pixel coordinates | integer index | (slow, fast) | Zero-indexed row-major convention |
| Panel coordinates | integer index | panel_id | Zero-indexed; aligns with dxtbx detector panels |

**Rule:** All internal variance-weighted computations SHALL use consistent units. When `--adu-per-photon` is provided:
- Target intensities are converted from ADU to photons
- Sigma readout values are divided by `adu_per_photon` to match
- Sigma floor values are divided by `adu_per_photon` to match

### Coordinate System

Array indexing follows dxtbx/DIALS conventions:

- **Panel axis:** First dimension of multi-panel arrays
- **Slow axis:** Second dimension (row index, typically detector Y)
- **Fast axis:** Third dimension (column index, typically detector X)

### Indexing Convention

- Arrays SHALL use 0-indexed access.
- Panel IDs SHALL be integers in range `[0, n_panels - 1]`.
- Experiment indices SHALL be integers in range `[0, n_experiments - 1]`.

---

## Core Data Types (Normative)

### ImageData

**Definition:** Raw detector image pixel values loaded from a crystallographic experiment.

**Shape Contract:** `[panel, slow, fast]` where:
- `panel` — Number of detector panels (from `Experiment.detector`)
- `slow` — Number of rows per panel
- `fast` — Number of columns per panel

**Fields:**

| Field | Type | Required | Contract |
|-------|------|----------|----------|
| `data` | `np.ndarray` | Yes | Shape SHALL be `[panel, slow, fast]`. Dtype SHALL be `float32`. |

**Invariants:**
1. Shape MUST match the detector geometry from the associated `Experiment`.
2. Negative pixel values indicate untrusted regions (per DIALS convention: `hotpix_mask=data<0`).

### TrustedMask

**Definition:** Boolean mask indicating which pixels are valid for analysis.

**Shape Contract:** `[panel, slow, fast]` — MUST match `ImageData.data.shape`.

**Fields:**

| Field | Type | Required | Contract |
|-------|------|----------|----------|
| `trusted_mask` | `np.ndarray` | Yes | Shape SHALL match `data`. Dtype SHALL be `bool`. |

**Polarity (CRITICAL):**
- **`True` = trusted/include** — Pixel SHALL be included in analysis.
- **`False` = untrusted/exclude** — Pixel SHALL be excluded from analysis.

This follows DIALS convention. The polarity is validated on load: if fewer than 50% of pixels are `True`, the mask is considered inverted and loading SHALL fail with `ValueError`.

**Invariants:**
1. Shape MUST match associated `ImageData`.
2. Polarity MUST be `True=trusted` per DIALS convention.
3. When no mask file is provided, all pixels SHALL be trusted (all `True`).

### SigmaReadoutMap

**Definition:** Per-pixel calibrated readout noise tensor for variance-weighted loss computation.

**Shape Contract:** `[panel, slow, fast]` — MUST match `ImageData.data.shape`.

**Fields:**

| Field | Type | Required | Contract |
|-------|------|----------|----------|
| `sigma_readout_map` | `np.ndarray` or `None` | No | If present, shape SHALL match `data`. Dtype SHALL be `float32`. |
| `sigma_readout_map_source` | `str` or `None` | No | Provenance: `"cli_map"`, `"external_lookup"`, or `None`. |
| `sigma_readout_map_metadata` | `dict` or `None` | No | Additional provenance metadata (path, lookup_key, tile_count). |

**Value Constraints:**
1. All values SHALL be strictly positive (`> 0.0`).
2. All values SHALL be finite (no `NaN` or `Inf`).
3. Values SHALL be in ADU unless `--adu-per-photon` triggers unit conversion.

**Supported Formats:**
- `.npy` — NumPy array file with shape `[panel, slow, fast]`
- `.npz` — NumPy archive; looks for key `"sigma"` first, then single-array fallback
- Pickle — Tuple/list of per-panel arrays (numpy or flex); panel count MUST match detector

**Invariants:**
1. When loaded from CLI (`--sigma-map`), source is `"cli_map"`.
2. When extracted from `Experiment.imageset.external_lookup`, source is `"external_lookup"`.
3. Provenance MUST be tracked for telemetry and reproducibility.

### SigmaReadoutScalar

**Definition:** Scalar readout noise value applied uniformly to all pixels.

**Fields:**

| Field | Type | Required | Contract |
|-------|------|----------|----------|
| `sigma_rdout` | `float` | No | If provided via CLI `--sigma-rdout`, SHALL be `> 0.0`. |

**Priority Resolution:**
1. CLI scalar (`--sigma-rdout`) — Highest priority; broadcasts to full tensor shape.
2. Calibrated map (`--sigma-map` or `external_lookup`) — Used when CLI scalar absent.
3. No source — CLI SHALL abort with actionable error message.

---

## Fundamental Computations (Normative)

### Variance Model

**Purpose:** Compute per-pixel variance for chi-squared weighting in refinement loss.

**Formula:**
```
V = max(I_model + σ_readout², σ_floor²)
```

**Inputs:**
- `I_model` — Predicted model intensity per pixel. Type: `torch.Tensor`. Units: target units (ADU or photons).
- `σ_readout` — Readout noise per pixel. Type: `torch.Tensor`. Units: MUST match `I_model`.
- `σ_floor` — Variance floor guard. Type: `float` or `torch.Tensor`. Units: MUST match `I_model`.

**Output:**
- `V` — Per-pixel variance. Type: `torch.Tensor`. Shape: same as `I_model`. Values SHALL be `≥ σ_floor²`.

**Constraints:**
1. `I_model` in variance calculation SHALL be detached from autograd graph (IRLS approach to prevent "attraction to zero").
2. `σ_readout²` is added in quadrature (Poisson + readout noise model).
3. `σ_floor²` provides a minimum variance to prevent infinite weights when `I_model → 0`.
4. Default `σ_floor = 1.0` in target units per CLI default.

### Variance-Weighted Chi-Squared Loss

**Purpose:** Compute chi-squared loss for LBFGS/Adam optimization.

**Formula:**
```
χ² = Σ[(I_model - I_obs)² / V] over masked pixels
```

**Inputs:**
- `I_model` — Predicted intensities `[panel, slow, fast]`. Type: `torch.Tensor`.
- `I_obs` — Observed target intensities `[panel, slow, fast]`. Type: `torch.Tensor`.
- `V` — Per-pixel variance from Variance Model. Type: `torch.Tensor`.
- `mask` — Boolean loss mask `[panel, slow, fast]`. Type: `torch.Tensor` with `dtype=bool`.

**Output:**
- `χ²` — Scalar chi-squared sum. Type: `torch.Tensor` (preserves autograd graph).
- `masked_mse` — Mean squared error over masked pixels (for telemetry).
- `masked_pixels` — Count of pixels where `mask=True`.
- `clamped_pixels` — Count of pixels where variance floor was applied.

**Constraints:**
1. Summation SHALL only include pixels where `mask=True`.
2. The ratio `clamped_pixels / masked_pixels` SHALL be reported in telemetry as `variance_floor_clamp_fraction`.
3. When `masked_pixels = 0`, loss SHALL raise `ValueError` with message "Loss mask contains no valid pixels".

---

## Validation Rules (Normative)

### Input Validation

#### Sigma Readout Validation

1. CLI scalar `--sigma-rdout` SHALL be validated: value MUST be `> 0.0`.
2. Calibrated sigma map SHALL be validated:
   - Shape MUST match `data.shape` exactly.
   - All values MUST be strictly positive (`> 0.0`).
   - All values MUST be finite (no `NaN`, no `Inf`).
3. If no sigma source is available (no CLI scalar, no calibrated map, no external_lookup metadata), the CLI SHALL refuse to run and emit an actionable error message.

#### Trusted Mask Validation

1. Mask shape MUST match `data.shape` exactly.
2. Mask polarity MUST be `True=trusted`. Validation: if `mean(mask) < 0.5`, the mask appears inverted and loading SHALL fail.
3. Mask dtype MUST be `bool` or convertible to `bool`.

#### Array Shape Validation

1. All per-pixel arrays (`data`, `trusted_mask`, `sigma_readout_map`, `background_image`) MUST have identical shape `[panel, slow, fast]`.
2. Panel count in sigma map (from pickle tuple/list) MUST match detector panel count.

### Output Validation

1. Variance tensor SHALL have no values `< σ_floor²`.
2. Chi-squared loss SHALL be non-negative.
3. Telemetry SHALL include `variance_floor_clamp_fraction` in range `[0.0, 1.0]`.

---

## Error Conditions (Normative)

| Condition | Required Behavior |
|-----------|-------------------|
| `--sigma-rdout <= 0` | SHALL raise `ValueError` with message containing "must be > 0" |
| Sigma map file not found | SHALL raise `FileNotFoundError` with path in message |
| Sigma map contains NaN or Inf | SHALL raise `ValueError` with message containing "NaN or Inf" and file path |
| Sigma map contains non-positive values | SHALL raise `ValueError` with message containing "non-positive" and file path |
| Sigma map shape mismatch | SHALL raise `ValueError` with message containing actual shape, expected shape, and reference to spec-db-core.md |
| Trusted mask appears inverted (`mean < 0.5`) | SHALL raise `ValueError` with message containing percentage of True pixels and reference to polarity convention |
| No sigma source available | SHALL raise `ValueError` with message listing required options (`--sigma-rdout`, `--sigma-map`, `external_lookup`) |
| Loss mask has no valid pixels | SHALL raise `ValueError` with message "Loss mask contains no valid pixels" |
| Prediction/target shape mismatch | SHALL raise `ValueError` with both shapes in message |
| Sigma map `.npz` has multiple arrays but none named "sigma" | SHALL raise `ValueError` with message instructing to provide single array or name it "sigma" |

**No Silent Failures:** Implementations MUST NOT silently produce incorrect results. When requirements cannot be met, implementations SHALL fail explicitly with descriptive error messages that include:
- The specific constraint violated
- The actual value(s) that caused the violation
- Reference to the relevant spec section when applicable

---

## Structure Factor Grid Construction (Normative)

### build_structure_factor_grid

**Purpose:** Construct a dense 3D HKL grid and ASU mapping from MTZ reflections for nanobrag_torch simulation.

**Signature:**
```python
build_structure_factor_grid(indices, amplitudes, device=None, halo=False) -> Tuple[torch.Tensor, Dict, torch.Tensor]
```

**Inputs:**

| Parameter | Type | Contract |
|-----------|------|----------|
| `indices` | `array-like` | Shape SHALL be `(n_reflections, 3)`. Dtype SHALL be `int`. Miller indices `(h, k, l)`. |
| `amplitudes` | `array-like` | Shape SHALL be `(n_reflections,)`. Dtype SHALL be `float`. Structure factor amplitudes `\|F\|`. |
| `device` | `torch.device` or `None` | Optional. Defaults to `torch.device('cpu')` when `None`. |
| `halo` | `bool` | Optional. Default `False`. When `True`, adds ±1 padding to each axis for tricubic interpolation (REFINE-005). |

**Output:**
Returns a tuple `(grid, metadata, asu_map)`:

| Element | Type | Contract |
|---------|------|----------|
| `grid` | `torch.Tensor` | Shape `[h_range, k_range, l_range]`. Dtype `float32`. Dense grid of structure factor amplitudes. |
| `metadata` | `dict` | Grid bounds and statistics (see table below). |
| `asu_map` | `torch.Tensor` | Shape same as `grid`. Dtype `int32`. ASU index per voxel; `-1` for unpopulated cells. |

**Metadata Dict Fields:**

| Key | Type | Contract |
|-----|------|----------|
| `h_min`, `h_max` | `int` | HKL bounds along h-axis (including halo if enabled). |
| `k_min`, `k_max` | `int` | HKL bounds along k-axis (including halo if enabled). |
| `l_min`, `l_max` | `int` | HKL bounds along l-axis (including halo if enabled). |
| `h_range`, `k_range`, `l_range` | `int` | Grid dimensions (h_max - h_min + 1, etc.). |
| `n_reflections` | `int` | Total input reflections. |
| `n_in_range` | `int` | Reflections mapped into grid. |
| `in_range_fraction` | `float` | Fraction of reflections in range `[0.0, 1.0]`. |
| `grid_nonzero` | `int` | Count of non-zero grid cells. |
| `grid_min`, `grid_max`, `grid_mean` | `float` | Grid amplitude statistics. |
| `has_halo` | `bool` | Whether halo padding was applied (REFINE-005). |
| `n_unique_asu` | `int` | Number of unique ASU indices assigned. |

**Behavior:**

1. Grid bounds SHALL be computed from min/max of input `indices` along each axis.
2. When `halo=True`, grid bounds SHALL be extended by ±1 on each axis (REFINE-005, TORCH-REFINE-002D).
3. Halo cells SHALL be initialized to zero (default_F fallback prevention).
4. Per SCALE-001: Amplitudes SHALL NOT be scaled by `spot_scale_override`. Scaling is applied post-simulation per SCALE-002.
5. ASU mapping uses Friedel-pair canonicalization: `(h,k,l)` maps to `(h,k,l)` or `(-h,-k,-l)` deterministically.

**Error Conditions:**

| Condition | Behavior |
|-----------|----------|
| `torch` not importable | SHALL raise `ImportError` with message containing "torch is required" |

**Cross-References:**
- `spec-db-workflow.md` §Stage B: `metadata['has_halo']` controls tricubic interpolation behavior.
- SCALE-001, SCALE-002: Structure factor scaling policy.
- REFINE-005, TORCH-REFINE-002D: Halo padding for boundary interpolation.

---

## Calibration Metadata Loading (Normative)

### load_calibration_metadata

**Purpose:** Load DiffBragg calibration metadata from config_torch.json for intensity alignment.

**Signature:**
```python
load_calibration_metadata(config_json_path) -> Dict[str, Any]
```

**Input:**

| Parameter | Type | Contract |
|-----------|------|----------|
| `config_json_path` | `str` or `Path` | Path to `config_torch.json`. File SHALL exist. |

**Output:**

| Key | Type | Contract |
|-----|------|----------|
| `spot_scale_override` | `float` | DiffBragg scale factor. SHALL be `> 0`. Per SCALE-002, `sqrt(spot_scale_override)` is applied post-simulation. |
| `beam_flux` | `float` | Beam flux in photons/s. SHALL be `> 0`. |
| `beam_exposure` | `float` | Exposure time in seconds. SHALL be `> 0`. |
| `beamsize_mm` | `float` or `None` | Beam size in mm. Optional; `None` when not present in config. |
| `N_cells` | `tuple[int, int, int]` or `None` | Crystal mosaic domain counts. Optional; `None` when not present. |

**Error Conditions:**

| Condition | Behavior |
|-----------|----------|
| File does not exist | SHALL raise `FileNotFoundError` with path and expected format |
| `crystal.scale_override` missing | SHALL raise `KeyError` with path and "scale_override" |
| `beam.flux` or `beam.exposure` missing | SHALL raise `KeyError` with path and missing field |
| `spot_scale_override <= 0` | SHALL raise `ValueError` with actual value and "must be positive" |
| `beam_flux <= 0` or `beam_exposure <= 0` | SHALL raise `ValueError` with actual values |
| `N_cells` present but length ≠ 3 | SHALL raise `ValueError` with actual length |

**Cross-References:**
- SCALE-002: Post-simulation sqrt(spot_scale_override) application.
- `spec-db-interfaces.md` §Calibration Configuration: `--torch-config` CLI parameter.

---

### load_refined_mtz

**Purpose:** Load refined structure factors from DiffBragg-refined MTZ file.

**Signature:**
```python
load_refined_mtz(mtz_path, column="F") -> Tuple[np.ndarray, np.ndarray]
```

**Inputs:**

| Parameter | Type | Contract |
|-----------|------|----------|
| `mtz_path` | `str` or `Path` | Path to refined MTZ file. File SHALL exist. |
| `column` | `str` | MTZ column label for amplitude data. Default `"F"`. |

**Output:**
Returns a tuple `(indices, amplitudes)`:

| Element | Type | Contract |
|---------|------|----------|
| `indices` | `np.ndarray` | Shape `(n_reflections, 3)`. Dtype `int32`. Miller indices. |
| `amplitudes` | `np.ndarray` | Shape `(n_reflections,)`. Dtype `float32`. Refined `\|F\|` values. |

**Behavior:**

1. Per SCALE-001: Amplitudes SHALL NOT be scaled (pass-through).
2. MTZ parsing uses `iotbx.mtz` to extract Miller arrays.
3. Column matching searches for label containing `column` with type hint `"amplitude"`.
4. Returns CPU numpy arrays (device-neutral per runtime checklist).

**Error Conditions:**

| Condition | Behavior |
|-----------|----------|
| File does not exist | SHALL raise `FileNotFoundError` with path |
| `iotbx.mtz` not importable | SHALL raise `ImportError` with import error |
| MTZ parsing fails | SHALL raise `ValueError` with path and parse error |
| Column not found | SHALL raise `ValueError` listing available arrays |
| Indices shape ≠ `(n, 3)` | SHALL raise `ValueError` with actual shape |
| Amplitudes length ≠ indices length | SHALL raise `ValueError` with both shapes |

**Cross-References:**
- SCALE-003, SCALE-004: Refined MTZ for parity testing.
- `spec-db-interfaces.md` §Refined MTZ Enforcement: `--refined-mtz` fail-fast behavior.

---

## References (Informative)

- DIALS documentation: trusted mask polarity convention
- `spec-db-runtime.md` — Execution requirements, device handling
- `spec-db-workflow.md` — Processing pipeline, stage ordering
- `spec-db-interfaces.md` — CLI parameter precedence
- `docs/architecture/dbex/physics/loss.idl.md` — Loss function API contract
