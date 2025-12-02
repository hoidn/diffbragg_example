# Torch HDF5 Writer IDL Contract

**Module**: `dbex.io.writer`
**Status**: Active (ARCH-REFINE-001 Phase C.2, C.4, D.1)
**Normative References**:
- `docs/spec-db-workflow.md` §§33-45 (RefinementEngine/telemetry contract)
- `docs/spec-db-workflow.md` §§70-75 (staging and outputs)
- `docs/spec-db-core.md` §§57-68 (variance model)
- `docs/spec-db-core.md` §§86-90 (variance computation)
- `docs/findings.md` DIAGNOSTICS-001, PHYSICS-LOSS-001, PHYSICS-LOSS-003, TORCH-CLI-004, REFINE-010

---

## Overview

`dbex.io.writer` provides the canonical torch backend HDF5 writer, consolidating ROI scoring, telemetry serialization, and `/torch_diagnostics` schema emission. Extracted from `dbex.refine_one._write_torch_outputs` in ARCH-REFINE-001 Phase C.2 to enable shared reuse across CLI and test tools.

### Key Principles

1. **Schema Stability**: HDF5 `/torch_diagnostics` group is byte-for-byte compatible with prior implementations (DIAGNOSTICS-001)
2. **Telemetry Provenance**: All variance/loss/sigma metadata is recorded with source citations (PHYSICS-LOSS-001)
3. **Multi-Stage Support**: Accepts Dict[str, RefinementTelemetry] for Stage A/B/C telemetry aggregation (ARCH-ENGINE-003)
4. **ROI Scoring Parity**: Uses `score_trainer.roi_check.roiCheck` per legacy DiffBragg equivalence
5. **Score Coercion**: Robust handling of mocked/non-scalar values via explicit float() casting (TORCH-CLI-004)

---

## ROI Analysis Payload (ARCH-BRIDGE-RESP-001 Phase A.2)

### Overview

Starting in Phase B, `write_torch_outputs` will accept typed ROI analysis payloads (`ROIAnalysisPayload` from `dbex.io.roi_analysis`) to separate ROI scoring (Nelder-Mead optimization) from HDF5 serialization. This section documents the new typed interface that will replace the current inline scoring loop.

### Data Types

**`ROITriptych`** (dataclass):
- **Fields**:
  - `panel_id: int` — DIALS detector panel ID (0-indexed)
  - `bbox: Tuple[int, int, int, int]` — Bounding box (x0, x1, y0, y1) with x1/y1 exclusive
  - `data: np.ndarray` — Observed target intensities (shape: ny, nx) in target units (ADU or photons)
  - `background: np.ndarray` — Background image (shape: ny, nx) matching target units
  - `bragg: np.ndarray` — Simulated Bragg intensities (shape: ny, nx) matching target units
- **Spec References**: docs/spec-db-core.md §§20-48 (array ordering, bbox semantics, unit modes)
- **Constraints**:
  - All arrays numpy-only (no torch tensors) for h5py serialization boundary
  - Background SHALL NOT contain NaN values
  - Shape consistency: data.shape == background.shape == bragg.shape

**`ROIAnalysisPayload`** (dataclass):
- **Fields**:
  - `triptych: ROITriptych` — Cropped data/background/bragg arrays and metadata
  - `score: Optional[float]` — Per-ROI quality metric from roiCheck (0-1, higher=better)
  - `optimal_scale: float` — Bragg intensity scale factor from Nelder-Mead (scalar >= 0)
  - `variance: Optional[np.ndarray]` — Variance array V = max(I_model + sigma_readout^2, sigma_floor^2) per spec-db-core.md §§86-90 (shape: ny, nx)
  - `model: Optional[np.ndarray]` — Optimized model image (background + optimal_scale * bragg) (shape: ny, nx)
- **Spec References**: docs/spec-db-core.md §§86-90 (variance computation), docs/spec-db-workflow.md §§70-75 (staging outputs)
- **Constraints**:
  - Variance must be strictly positive and finite on trusted pixels (zero/NaN sigma is non-compliant per spec-db-core.md §38)
  - Score provenance: Computed via `score_trainer.roi_check.roiCheck.score(data, model)`
  - Optimal scale: Derived from minimizing `1 - CHECKER.score()` over Bragg scale parameter

### Helper: `build_roi_payloads_from_arrays`

```python
def build_roi_payloads_from_arrays(
    target: np.ndarray,
    background: np.ndarray,
    bragg: np.ndarray,
    pids: List[int],
    bbox: List[Tuple[int, int, int, int]],
    scores: Optional[List[float]] = None,
    scales: Optional[List[float]] = None,
) -> List[ROIAnalysisPayload]
```

**Purpose**: Package existing ROI arrays into typed payloads without mutating or optimizing. This helper performs only array slicing and dataclass construction; it does NOT run Nelder-Mead optimization or compute variance.

**Inputs**:
- `target`: Full-detector target intensities (n_panels, slow, fast) in ADU or photons
- `background`: Full-detector background image (n_panels, slow, fast) matching target units
- `bragg`: Full-detector simulated Bragg intensities (n_panels, slow, fast) matching target units
- `pids`: Panel IDs per ROI (length n_rois)
- `bbox`: Bounding boxes per ROI (length n_rois), each (x0, x1, y0, y1) with x1/y1 exclusive
- `scores`: Optional pre-computed per-ROI scores (length n_rois). If None, all payloads have score=None
- `scales`: Optional pre-computed optimal Bragg scales (length n_rois). If None, defaults to 1.0

**Outputs**:
- List of `ROIAnalysisPayload` instances (length n_rois), one per ROI. Variance and model fields are set to None (computed downstream).

**Data Dependencies** (see docs/data_dependency_manifest.md):
- External: Target/background/bragg arrays from DataLoad + RefinementEngine final forward model
- Telemetry: ROI panel IDs (`pids`) and bounding boxes (`bbox`) from DataLoad
- Optional: Pre-computed scores/scales from upstream ROI scoring helper (Phase B)

**Future Wiring** (Phase B):
1. Dedicated ROI scoring helper will call `build_roi_payloads_from_arrays` after running Nelder-Mead
2. Scoring helper will populate `score`, `optimal_scale`, `variance`, and `model` fields
3. `write_torch_outputs` will consume typed `List[ROIAnalysisPayload]` instead of raw arrays
4. Writer focuses solely on HDF5 serialization (no inline optimization)

### Dataset Mapping

When `write_torch_outputs` accepts `List[ROIAnalysisPayload]` in Phase B, HDF5 datasets will map as follows:

| HDF5 Dataset | Source Field | Shape | dtype |
|--------------|--------------|-------|-------|
| `/data/roi<i>` | `payloads[i].triptych.data` | (ny, nx) | float32 or float64 |
| `/bg/roi<i>` | `payloads[i].triptych.background` | (ny, nx) | float32 or float64 |
| `/bragg/roi<i>` | `payloads[i].triptych.bragg` | (ny, nx) | float32 or float64 |
| `/model/roi<i>` | `payloads[i].model` | (ny, nx) | float32 or float64 |
| `/variance/roi<i>` | `payloads[i].variance` | (ny, nx) | float32 or float64 |
| `/score` | `[p.score for p in payloads]` | (n_rois,) | float32 |
| `/bragg_scale` | `[p.optimal_scale for p in payloads]` | (n_rois,) | float32 |

**Provenance Telemetry**: `/torch_diagnostics` group will include:
- `roi_scoring_method: str` — "nelder_mead" (Phase B) or "inline" (legacy, Phase A)
- `roi_checker: str` — "score_trainer.roi_check.roiCheck" (legacy parity)

---

## API: write_torch_outputs

### Signature

```python
def write_torch_outputs(
    args,
    data_load,
    bragg,
    inputs,
    masked_mse,
    hkl_telemetry,
    refine_telemetry=None,
    sigma_readout_provenance=None,
    sigma_readout_reference_value=None,
    stage_artifacts=None,
) -> None
```

### Inputs

| Parameter | Type | Required | Contract | Provenance |
|-----------|------|----------|----------|------------|
| `args` | argparse.Namespace | Yes | CLI parser output with keys: `outFile` (str), `sigma_floor` (float, default 1.0), `adu_per_photon` (Optional[float]) | `create_parser()` in refine_one.py |
| `data_load` | `DataLoad` | Yes | Contains: `data` (np.ndarray [panels, slow, fast]), `background_image`, `detector` (dxtbx Detector), `pids` (panel IDs per ROI), `bbox` (ROI bounding boxes [x1,x2,y1,y2]) | `load_dataload()` via data_load.py |
| `bragg` | np.ndarray | Yes | Simulated Bragg intensities [panels, slow, fast], same shape as data_load.data, target units (post-ADU conversion if applicable) | Final forward model from refinement engine or Stage C |
| `inputs` | `RefinementInputs` | Yes | Namedtuple with: `target` (torch.Tensor), `loss_mask` (torch.Tensor bool), `panel_slices` (list), `trusted_mask` (per-panel mask) | `prepare_refinement_inputs()` via nanobrag_bridge.py |
| `masked_mse` | float | Yes | Masked mean squared error between target and Bragg (scalar) | Final loss from refinement or forward-only run |
| `hkl_telemetry` | Dict[str, Any] | Yes | Keys: `hkl_source` ("refined"/"raw"), `hkl_n_reflections` (int), `hkl_mean_amplitude` (float), `hkl_path` (str) | MTZ metadata from CLI via `build_structure_factor_grid()` |
| `refine_telemetry` | Optional[Dict[str, RefinementTelemetry] or RefinementTelemetry] | No | Multi-stage telemetry ({"A": telemetry_a, "B": telemetry_b, "C": telemetry_c}) or single RefinementTelemetry (legacy, mapped to {"A": telemetry}) | `RefinementEngine.telemetry()` or inline refinement |
| `sigma_readout_provenance` | Optional[str] | No | Human-readable description of sigma source ("cli_override", "calibrated_map", "external_lookup", etc.) per PHYSICS-LOSS-001 | `_resolve_sigma_readout()` in CLI |
| `sigma_readout_reference_value` | Optional[float] | No | Scalar sigma_readout in target units (after ADU→photon conversion if applicable) | `_resolve_sigma_readout()` in CLI |
| `stage_artifacts` | Optional[Dict[str, Any]] | No | Stage-specific metadata from `RefinementEngine.artifacts` containing stage artifacts (e.g., {"stage_b": StageBArtifacts}). When provided, Stage B baseline parity metrics (`stage_b_baseline_rel_diff`, `stage_b_baseline_abs_diff`, `stage_b_baseline_diff_path`) are sourced from StageBArtifacts; otherwise falls back to telemetry fields (ARCH-STAGE-CONTEXT-001 Phase B.4) | `RefinementEngine.artifacts` |

### Outputs

| Output | Format | Content | Schema Reference |
|--------|--------|---------|------------------|
| HDF5 `/torch_diagnostics` group | Attributes | `masked_mse` (float), `loss_mask_coverage` (float), `n_rois` (int), `target_shape` (str), `backend` ("nanobrag"), `sigma_floor` (float), optional: `adu_per_photon`, `sigma_readout_provenance`, `sigma_readout_reference_value` | docs/spec-db-workflow.md:70-75, DIAGNOSTICS-001 |
| HDF5 `/torch_diagnostics/hkl_telemetry` | Attributes | `hkl_source`, `hkl_n_reflections`, `hkl_mean_amplitude`, `hkl_path` | PHYSICS-LOSS-001 |
| HDF5 `/torch_diagnostics/refine_telemetry` | JSON string attribute | Serialized Dict[str, RefinementTelemetry.to_dict()] with Stage A/B/C keys | ARCH-ENGINE-003, PHYSICS-LOSS-003 |
| HDF5 ROI datasets | Datasets | Per-ROI: `data_<i>`, `model_<i>`, `bragg_<i>`, `bg_<i>`, `variance_<i>`, `score_<i>`, `bragg_scale_<i>` | REFINE-010, ROI scoring loop |

### Variance Computation

Per spec-db-core.md §86-90:
```
V = max(I_model + sigma_rdout^2, sigma_floor^2)
```

- `I_model`: Bragg model intensities (numpy array)
- `sigma_rdout`: `args.sigma_floor` (default 1.0) or `sigma_readout_reference_value` when provided
- `sigma_floor`: `args.sigma_floor` (variance floor in target units)

### ROI Scoring Loop

For each ROI:
1. Extract ROI sub-images from data/bragg/background using `pids` and `bbox`
2. Compute variance per pixel: `V_roi = np.maximum(bragg_roi + sigma_rdout**2, sigma_floor**2)`
3. Optimize `bragg_scale` via scipy.optimize.minimize to maximize `roiCheck.score(data_roi, bragg_scale**2 * bragg_roi + bg_roi)`
4. Store score (coerced via `float()` per TORCH-CLI-004), bragg_scale, and sub-images in HDF5 datasets

---

## Dependencies

### Direct Imports
- `h5py` (HDF5 I/O)
- `numpy` (array ops)
- `scipy.optimize.minimize` (ROI scoring optimization)
- `score_trainer.roi_check` (roiCheck scorer per legacy DiffBragg parity)
- `dbex.refinement.RefinementTelemetry` (telemetry dataclass serialization)

### Transitive Dependencies
- **External data**: Target intensities, background, detector geometry, ROI metadata via `DataLoad` (see docs/data_dependency_manifest.md §DataLoad)
- **MTZ**: Structure factor amplitudes and metadata via `hkl_telemetry` (see docs/data_dependency_manifest.md §HKL_Grid)
- **Telemetry**: Variance/loss/sigma provenance from refinement stages (PHYSICS-LOSS-001)

---

## Usage Patterns

### Pattern 1: CLI torch backend (multi-stage telemetry with artifacts)

```python
from dbex.io.writer import write_torch_outputs

# After refinement engine completes
write_torch_outputs(
    args=args,
    data_load=DL,
    bragg=final_bragg_np,
    inputs=inputs,
    masked_mse=final_mse,
    hkl_telemetry=hkl_telemetry,
    refine_telemetry=engine.telemetry(),  # Dict[str, RefinementTelemetry]
    sigma_readout_provenance=sigma_provenance,
    sigma_readout_reference_value=sigma_reference_value,
    stage_artifacts=engine.artifacts,  # Dict[str, StageArtifacts] (ARCH-STAGE-CONTEXT-001 Phase B.4)
)
```

### Pattern 2: Forward-only probe (no refine_telemetry)

```python
write_torch_outputs(
    args=args,
    data_load=DL,
    bragg=bragg_forward_np,
    inputs=inputs,
    masked_mse=forward_mse,
    hkl_telemetry=hkl_telemetry,
    # refine_telemetry=None (omitted)
    sigma_readout_provenance="external_lookup",
    sigma_readout_reference_value=1.5,
)
```

### Pattern 3: Test fixture with mocked telemetry

```python
# tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
mock_refine_telemetry = {
    "A": RefinementTelemetry(stage="A", chi_squared_initial=100.0, ...)
}
write_torch_outputs(
    args=mock_args,
    data_load=mock_dataload,
    bragg=mock_bragg,
    inputs=mock_inputs,
    masked_mse=1.23,
    hkl_telemetry=mock_hkl_telemetry,
    refine_telemetry=mock_refine_telemetry,
    # Score coercion (TORCH-CLI-004) prevents TypeError from mocked scores
)
```

---

## Validation & Testing

### Primary Selectors
- `pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` (CLI telemetry schema)
- `pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz` (HKL telemetry provenance)

### Validation Rules
1. `/torch_diagnostics` group must exist in output HDF5
2. All required attributes (`masked_mse`, `loss_mask_coverage`, `n_rois`, `target_shape`, `backend`) must be present
3. `refine_telemetry` JSON must deserialize to Dict[str, dict] with Stage keys
4. Variance computation must match spec-db-core.md:86-90 (max of model+sigma^2 and floor^2)
5. ROI datasets must follow naming convention `data_<i>`, `model_<i>`, etc.

---

## Maintenance Notes

- **Schema changes**: Treat `/torch_diagnostics` as a frozen contract (DIAGNOSTICS-001); any additions must be optional attributes
- **Score coercion**: Always use `float(score)` when storing roiCheck results to handle mocked/non-scalar values (TORCH-CLI-004)
- **Telemetry serialization**: `RefinementTelemetry.to_dict()` must remain JSON-serializable; no numpy arrays or torch tensors
- **Variance provenance**: When adding new sigma sources, update `sigma_readout_provenance` docs and ensure telemetry records them
- **ROI scoring**: `roiCheck.score()` API is legacy; consider documenting its contract if it ever changes upstream

---

## Change Log

- **2025-12-02 (ARCH-STAGE-CONTEXT-001 Phase B.4)**: Added `stage_artifacts` parameter to support sourcing Stage B baseline parity metrics from StageBArtifacts. When provided, metrics are pulled from artifacts; otherwise falls back to telemetry fields for backward compatibility. Usage patterns updated to reflect engine.artifacts parameter.
- **2025-12-01 (Phase D.1)**: IDL contract published; docstrings updated to reference this file
- **2025-12-01 (Phase C.4)**: Removed compatibility alias `_write_torch_outputs` from dbex.refine_one; canonical module is now the sole entrypoint
- **2025-12-01 (Phase C.2)**: Extracted from `dbex.refine_one._write_torch_outputs` to shared module `dbex.io.writer`; no schema changes, signature identical except parameter name (DL→data_load for API clarity)
