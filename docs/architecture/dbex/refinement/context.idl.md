# RefinementContext & JobContext IDL Contract

**Module**: `dbex.refinement.context`
**Status**: Active (ARCH-REFINE-001 Phase B.1, B.2, B.3)
**Normative References**:
- `docs/spec-db-workflow.md` §§48-84 (Refinement Protocol Architecture)
- `docs/spec-db-core.md` §§85-90 (HKL Grid Contracts)
- `docs/config_crosswalk.md` §3 (Config Mapping)
- `docs/findings.md` REFINE-005, REFINE-010, GRADIENT-004

---

## Overview

`RefinementContext` and `JobContext` are typed dataclasses introduced in ARCH-REFINE-001 to replace ad-hoc dict plumbing with explicit contracts. They ensure consistent geometry/HKL/calibration state flows through the RefinementEngine and Stage A/B/C wrappers.

### Key Principles

1. **Immutability**: Once built, contexts are read-only; stages extract fields but do not modify them
2. **Device Neutrality**: HKL tensors (hkl_grid, asu_map) may reside on any device; stages are responsible for `.to(device)`
3. **Lazy Computation**: Optional fields (asu_map, hkl_indices_grid, halo_mask) are populated only when CLI or upstream stages provide them (REFINE-005)
4. **Fallback Paths**: Stage B checks context.asu_map before calling `compute_hkl_asu_map`; missing fields trigger graceful fallbacks with clear warnings

---

## RefinementContext

### Field Contracts

| Field | Type | Nullability | Contract | Provenance |
|-------|------|------------|----------|------------|
| `refinement_inputs` | `RefinementInputs` | Required | Target/loss_mask/panel_slices per spec-db-core.md:20; `[panel, slow, fast]` ordering | `prepare_nanobrag_inputs()` via CLI |
| `detector` | dxtbx Detector | Required | Panel geometry; square pixels per config_crosswalk.md:30 | `load_dataload()` |
| `beam` | dxtbx Beam | Required | Wavelength/polarization per config_crosswalk.md:65-70 | `load_dataload()` |
| `crystal` | dxtbx Crystal | Required | Unit cell/orientation per config_crosswalk.md:75-80; may be perturbed | `load_dataload()` or perturbed copy |
| `hkl_grid` | torch.Tensor | Required | 3D structure factor grid `[h_range, k_range, l_range]`, dtype float32, per spec-db-core.md:85-90 | `build_structure_factor_grid()` |
| `hkl_metadata` | Dict[str, Any] | Required | Keys: `has_halo` (bool), `h_min/h_max`, `k_min/k_max`, `l_min/l_max`, `n_unique_asu` (optional) | `build_structure_factor_grid()` |
| `baseline_crystal` | dxtbx Crystal | Optional | Baseline for misset extraction (Stage A computes `delta_misset`); required when crystal is perturbed | CLI deep-copy of crystal |
| `baseline_detector` | dxtbx Detector | Optional | Baseline for Stage C detector offset reference; required when Stage C enabled | CLI deep-copy of detector |
| `asu_map` | torch.Tensor | Optional | ASU index mapping `[h_range, k_range, l_range]`, dtype int32, values ≥-1 (halo=-1); from `build_structure_factor_grid()` | CLI via JobContext |
| `hkl_indices_grid` | np.ndarray | Optional | Miller indices `[h_range, k_range, l_range, 3]` (h,k,l tuples); Stage B uses when calling `compute_hkl_asu_map` fallback | CLI or reconstructed from hkl_metadata bounds |
| `halo_mask` | np.ndarray | Optional | Boolean mask `[h_range, k_range, l_range]` marking halo cells (True=halo, False=data); passed to `compute_hkl_asu_map` when asu_map is missing | CLI extras (if provided) |
| `extras` | Dict[str, Any] | Always present (default `{}`) | Future extensions (job provenance, telemetry sinks, etc.) | Reserved |

### Validation Rules (enforced by `build_refinement_context`)

1. `hkl_grid` must be `torch.Tensor` (not np.ndarray)
2. `hkl_metadata` must contain `'has_halo'` key (Stage B/C require this per spec-db-workflow.md:53-54)
3. `refinement_inputs` must not be None
4. If `asu_map` provided, must be `torch.Tensor` with `shape == hkl_grid.shape`
5. If `hkl_indices_grid` provided, must be `np.ndarray`
6. If `halo_mask` provided, must be `np.ndarray`

### Construction

```python
from dbex.refinement.context import build_refinement_context

context = build_refinement_context(
    refinement_inputs=inputs,
    detector=detector,
    beam=beam,
    crystal=crystal,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    baseline_crystal=baseline_crystal,
    baseline_detector=baseline_detector,
    job_context=job_context,  # ARCH-REFINE-001 Phase B.3: auto-copies asu_map/hkl_indices_grid/halo_mask
)
```

**Automatic Population from JobContext**: If `job_context` is provided and `asu_map`/`hkl_indices_grid`/`halo_mask` are None, `build_refinement_context` copies them from `job_context.asu_map`, `job_context.extras['hkl_indices_grid']`, and `job_context.extras['halo_mask']` respectively.

---

## JobContext

### Field Contracts

| Field | Type | Nullability | Contract | Provenance |
|-------|------|------------|----------|------------|
| `cli_args` | argparse.Namespace or dict | Required | CLI parser output per refine_one.py `create_parser()` | CLI entry point |
| `dataload` | `DataLoad` | Required | Experiment/detector/beam/crystal/reflections from `load_dataload()` | CLI |
| `calibration_metadata` | Dict[str, Any] | Optional | torch_config.json payload (spot_scale_override, beam flux/exposure/beamsize, N_cells) per spec-db-workflow.md:34-44 | CLI `load_calibration_metadata()` |
| `sigma_provenance` | str | Required (non-empty) | "cli_override", "calibrated_map", "external_lookup", etc.; must be documented for telemetry per PHYSICS-LOSS-001 | CLI `_resolve_sigma_readout()` |
| `sigma_reference_value` | float | Required (> 0) | Scalar sigma_readout reference in target units (after ADU→photon conversion if applicable) per spec-db-core.md:32-68 | CLI `_resolve_sigma_readout()` |
| `refinement_config` | `RefinementConfig` | Required | Device/dtype/sigma_floor/stage flags per spec-db-workflow.md:36-42 | CLI constructor or loaded config |
| `hkl_metadata` | Dict[str, Any] | Required | HKL grid dimensions from `build_structure_factor_grid()` (same dict as RefinementContext.hkl_metadata) | `build_structure_factor_grid()` |
| `asu_map` | np.ndarray or torch.Tensor | Optional | ASU mapping tensor (converted to torch.Tensor when threading into RefinementContext) | `build_structure_factor_grid()` |
| `spot_scale_override` | float | Required (> 0, default 1.0) | Spot scale applied post-simulation per SCALE-002 | CLI calibration or override |
| `hkl_source` | str | Required (default "raw") | "refined" or "raw"; HKL provenance for telemetry per spec-db-workflow.md:43-46 | CLI MTZ path analysis |
| `hkl_path` | str | Optional | MTZ file path (for telemetry) | CLI args.mtzFile |
| `extras` | Dict[str, Any] | Always present (default `{}`) | Keys: `hkl_indices_grid` (np.ndarray), `halo_mask` (np.ndarray), future extensions | CLI optional extras |

### Validation Rules (enforced by `build_job_context`)

1. `sigma_reference_value` must be strictly positive
2. `sigma_provenance` must be non-empty string
3. `hkl_metadata` must contain `'has_halo'` key
4. `spot_scale_override` must be strictly positive
5. `hkl_source` must be "refined" or "raw"
6. `dataload` and `refinement_config` must not be None

### Construction

```python
from dbex.refinement.context import build_job_context

job_context = build_job_context(
    cli_args=args,
    dataload=DL,
    calibration_metadata=calibration_metadata,
    sigma_provenance=sigma_provenance,
    sigma_reference_value=sigma_reference_target_units,
    refinement_config=refine_config,
    hkl_metadata=hkl_metadata,
    asu_map=asu_map,  # From build_structure_factor_grid
    spot_scale_override=spot_scale,
    hkl_source=hkl_source,
    hkl_path=hkl_path,
    extras={'hkl_indices_grid': hkl_indices_grid, 'halo_mask': halo_mask},  # Optional
)
```

---

## Usage Patterns

### Pattern 1: CLI builds JobContext → RefinementEngine builds RefinementContext

```python
# In refine_one.py::run_nanobrag_backend()
hkl_grid, hkl_metadata, asu_map = build_structure_factor_grid(...)
job_context = build_job_context(..., asu_map=asu_map, ...)

# In nanobrag_refinement.py::run_nanobrag_refinement()
context = build_refinement_context(..., job_context=job_context)  # Copies asu_map from job_context
engine_inputs = {'context': context, 'job_context': job_context, ...}
engine.run(engine_inputs)
```

### Pattern 2: Stage B checks context for pre-computed ASU map

```python
# In stage_b_impl.py::_build_stage_b_params()
if context is not None and hasattr(context, 'asu_map') and context.asu_map is not None:
    # Reuse CLI-built ASU map (REFINE-005)
    asu_indices = context.asu_map
    n_asu_unique = hkl_metadata.get("n_unique_asu", int(asu_indices.max().item()) + 1)
else:
    # Fallback: call compute_hkl_asu_map with cctbx
    hkl_indices_grid = context.hkl_indices_grid or reconstruct_from_metadata(...)
    halo_mask = context.halo_mask or hkl_metadata.get("halo_mask")
    asu_indices, n_asu_unique = compute_hkl_asu_map(hkl_indices_grid, crystal_symmetry, halo_mask=halo_mask)
```

### Pattern 3: Stage C warm-cache retargeting (GRADIENT-004)

Stage C warm-cache helpers (`_retarget_stage_a_detectors`) read `baseline_detector` and Stage A ROI metadata from context to rebuild cached detectors without recomputing HKL grids. This preserves autograd chains (see GRADIENT-004, REFINE-010).

---

## Maintenance Notes

- **Add new fields carefully**: All context fields must have clear normative provenance and validation rules
- **Document transitive dependencies**: If a field depends on external data (MTZ, DIALS reflections, etc.), cite the loader in `docs/data_dependency_manifest.md`
- **Preserve device neutrality**: Never add `.to(device)` calls in context builders; stages manage device placement
- **Update tests**: When adding fields, update `tests/dbex/test_torch_refine_smoke.py` fixtures to provide them

---

## Change Log

- **2025-12-01 (Phase B.3)**: Added `asu_map`, `hkl_indices_grid`, `halo_mask` to RefinementContext; `build_refinement_context` auto-copies from JobContext; Stage B reuses context.asu_map before falling back to `compute_hkl_asu_map` (REFINE-005)
- **2025-12-01 (Phase B.2)**: Added JobContext with CLI args, DataLoad, calibration metadata, sigma provenance, HKL source, and spot scale override
- **2025-12-01 (Phase B.1)**: Initial RefinementContext with refinement_inputs, detector, beam, crystal, hkl_grid, hkl_metadata, baseline_crystal, baseline_detector
