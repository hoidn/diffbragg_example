# Physics Forward Simulation IDL Contract

**Module**: `dbex.physics.forward`
**Status**: Active (ARCH-REFINE-001 Phase C.3, D.1) — TEST-ONLY
**Normative References**:
- `docs/spec-db-runtime.md` §4.1 (gradient profile, RUNTIME-001)
- `docs/spec-db-conformance.md` §§12-14 (DB-AT-010 acceptance)
- `docs/spec-db-core.md` §§57-68 (variance-weighted chi-squared)
- `docs/spec-db-workflow.md` §§30-45 (forward helper + telemetry expectations)
- `docs/development/testing_strategy.md` §§338-372 (gradcheck requirements)
- `docs/pytorch_runtime_checklist.md` §§27-30 (NANOBRAGG_DISABLE_COMPILE=1)
- `docs/findings.md` RUNTIME-001, SCALE-001, SCALE-002, GRADIENT-001, PHYSICS-LOSS-001, ARCH-FACTORY-001

---

## Overview

`dbex.physics.forward` provides gradient-preserving forward simulation utilities for DB-AT-010 gradcheck acceptance testing. This is a **TEST-ONLY** module: functions preserve autograd graphs by avoiding `.detach()` and `.numpy()` conversions, enabling `torch.autograd.gradcheck` validation of physics equations. Production LBFGS closures should use Stage A/B/C helpers instead.

### Key Principles

1. **Gradient Preservation**: No `.detach()`, `.numpy()`, or `.item()` calls that break autograd chains (GRADIENT-001)
2. **Tensor-Valued Overrides**: `crystal_overrides` dict enables direct tensor parameter injection without scalar extraction (GRADIENT-001)
3. **Device/Dtype Agnostic**: Supports CPU/CUDA and float32/float64 (float64 required for gradcheck per pytorch_runtime_checklist.md:27-30)
4. **Test-Only Scope**: Do not import in production LBFGS closures; use Stage A/B/C helpers for refinement
5. **NANOBRAGG_DISABLE_COMPILE=1**: Must run with `torch.compile` disabled per RUNTIME-001

---

## API: simulate_forward_torch

### Signature

```python
def simulate_forward_torch(
    inputs,  # RefinementInputs type
    detector,  # dxtbx Detector
    beam,  # dxtbx Beam
    crystal,  # dxtbx Crystal
    experiment,  # dxtbx Experiment
    hkl_indices: np.ndarray,
    hkl_amplitudes: np.ndarray,
    spot_scale_override: Optional[float] = None,
    device=None,
    dtype=None,
    crystal_overrides: Optional[dict] = None
) -> torch.Tensor
```

### Inputs

| Parameter | Type | Required | Contract | Provenance |
|-----------|------|----------|----------|------------|
| `inputs` | `RefinementInputs` | Yes | Namedtuple with: `target` (torch.Tensor), `loss_mask` (torch.Tensor bool), `panel_slices` (list), `global_scale_hint` (float) | `prepare_refinement_inputs()` via nanobrag_bridge.py |
| `detector` | dxtbx Detector | Yes | Panel geometry per spec-db-core.md:20; square pixels | `load_dataload()` via data_load.py |
| `beam` | dxtbx Beam | Yes | Wavelength/polarization per config_crosswalk.md:65-70 | `load_dataload()` via data_load.py |
| `crystal` | dxtbx Crystal | Yes | Unit cell/orientation per config_crosswalk.md:75-80 | `load_dataload()` or perturbed copy |
| `experiment` | dxtbx Experiment | Yes | DIALS Experiment (used by `create_crystal_config`) | `load_dataload()` via data_load.py |
| `hkl_indices` | np.ndarray | Yes | Miller indices [n_refl, 3], dtype int32 | MTZ via `build_structure_factor_grid()` |
| `hkl_amplitudes` | np.ndarray | Yes | Structure factor amplitudes [n_refl], dtype float32, unscaled per SCALE-001 | MTZ via `build_structure_factor_grid()` |
| `spot_scale_override` | Optional[float] | No | Scale factor (default 1.0); applied as `sqrt(spot_scale)` post-simulation per SCALE-002 | CLI calibration or test override |
| `device` | Optional[torch.device] | No | Target device (default cpu); gradcheck requires CPU for numerical stability | Test fixture or runtime config |
| `dtype` | Optional[torch.dtype] | No | Computation dtype (default float32); **use float64 for gradcheck** per pytorch_runtime_checklist.md:27-30 | Test fixture (float64) or runtime (float32) |
| `crystal_overrides` | Optional[Dict[str, torch.Tensor]] | No | Tensor-valued crystal parameters for gradcheck. Keys: `cell_a`, `cell_b`, `cell_c`, `cell_alpha`, `cell_beta`, `cell_gamma`. Tensors must have `requires_grad=True` to preserve gradient flow (GRADIENT-001). | Test fixture for DB-AT-010 gradcheck |

### Outputs

| Output | Type | Shape | Contract |
|--------|------|-------|----------|
| `bragg_torch` | torch.Tensor | [panel, slow, fast] | Per-panel Bragg intensities in target units with `sqrt(spot_scale_override)` applied differentiably per SCALE-002. Autograd graph preserved. |

### Validation Rules

1. `crystal_overrides` keys must be valid crystal parameter names: `cell_a`, `cell_b`, `cell_c`, `cell_alpha`, `cell_beta`, `cell_gamma`
2. When `crystal_overrides` provided, tensors must be torch.Tensor (not scalars) to enable gradient flow
3. `hkl_indices` and `hkl_amplitudes` must have matching first dimension (n_reflections)
4. `inputs.target` must have compatible shape for ROI stacking

### Exceptions

- `ImportError`: If `nanobrag_torch` is not available
- `ValueError`: If config creation fails, simulation errors, or invalid override keys

---

## Dependencies

### Direct Imports
- `torch` (autograd, tensors)
- `numpy` (array ops for HKL data)
- `nanobrag_torch.simulator.Simulator` (forward model)
- `nanobrag_torch.models.detector.Detector` (detector config)
- `nanobrag_torch.models.crystal.Crystal` (crystal config)

### Bridge Imports (lazy)
- `dbex.nanobrag_bridge.build_structure_factor_grid` (HKL grid construction)
- `dbex.nanobrag_bridge.create_beam_config` (beam config builder)
- `dbex.nanobrag_bridge.create_crystal_config` (crystal config builder)
- `dbex.nanobrag_bridge.create_detector_config` (detector config builder)
- `dbex.refinement.helpers.create_unified_simulator` (factory per ARCH-FACTORY-001)

### Transitive Dependencies
- **External data**: MTZ (HKL indices/amplitudes), DIALS Experiment (detector/beam/crystal geometry) — see docs/data_dependency_manifest.md §HKL_Grid, §DataLoad
- **Environment**: `NANOBRAGG_DISABLE_COMPILE=1` required per RUNTIME-001 to prevent torch.compile caching issues during gradcheck

---

## Usage Patterns

### Pattern 1: DB-AT-010 gradcheck (unit cell parameters)

```python
from dbex.physics.forward import simulate_forward_torch
import torch

# Prepare tensor-valued override with gradient
cell_a_tensor = torch.tensor([79.0], dtype=torch.float64, requires_grad=True)
crystal_overrides = {"cell_a": cell_a_tensor}

# Forward simulation with gradient preservation
bragg_torch = simulate_forward_torch(
    inputs=inputs,
    detector=detector,
    beam=beam,
    crystal=crystal,
    experiment=experiment,
    hkl_indices=hkl_indices,
    hkl_amplitudes=hkl_amplitudes,
    spot_scale_override=1.0,
    device=torch.device("cpu"),
    dtype=torch.float64,  # Required for gradcheck
    crystal_overrides=crystal_overrides,
)

# Gradcheck validation
from dbex.physics.loss import compute_masked_mse_loss
loss = compute_masked_mse_loss(bragg_torch, target, mask, sigma_readout)
torch.autograd.gradcheck(
    lambda a: compute_masked_mse_loss(
        simulate_forward_torch(..., crystal_overrides={"cell_a": a}),
        target, mask, sigma_readout
    ),
    cell_a_tensor,
    atol=1e-5, rtol=1e-3
)
```

### Pattern 2: Forward-only probe (no gradcheck)

```python
# No crystal_overrides, default float32
bragg_torch = simulate_forward_torch(
    inputs=inputs,
    detector=detector,
    beam=beam,
    crystal=crystal,
    experiment=experiment,
    hkl_indices=hkl_indices,
    hkl_amplitudes=hkl_amplitudes,
    spot_scale_override=spot_scale,
    device=torch.device("cuda:0"),
    dtype=torch.float32,
)
```

---

## Validation & Testing

### Primary Selectors
- `pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck` (DB-AT-010 acceptance)
  - `test_gradcheck_cell_a`, `test_gradcheck_cell_b`, `test_gradcheck_cell_c`
  - `test_gradcheck_cell_alpha`, `test_gradcheck_cell_beta`
  - Requires: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`, `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`

### Validation Rules
1. Autograd graph must be preserved (no `.detach()` or `.item()` calls on gradient-enabled tensors)
2. `crystal_overrides` tensors with `requires_grad=True` must flow through config builder without detachment
3. Gradcheck must pass with `atol=1e-5, rtol=1e-3` for unit cell parameters (DB-AT-010)
4. Spot scale `sqrt(spot_scale_override)` must be applied as differentiable torch op (SCALE-002)

---

## Maintenance Notes

- **Gradient preservation**: Never add `.item()`, `.numpy()`, or `.detach()` calls on tensors that participate in autograd
- **Crystal overrides**: If adding new override keys, update the validation logic and ensure config builders accept tensor values without scalar extraction
- **Bridge coupling**: This module imports from `dbex.nanobrag_bridge` for config builders; if bridge refactors, verify imports remain functional
- **Test-only scope**: Do not import this function in production LBFGS closures (`dbex/refinement/stage_*.py`, `dbex/nanobrag_refinement.py`); use Stage A/B/C helpers instead
- **NANOBRAGG_DISABLE_COMPILE=1**: Document this requirement in test selectors; gradcheck will fail if torch.compile caches incorrect graphs

---

## Change Log

- **2025-12-01 (Phase D.1)**: IDL contract published; docstrings updated to reference this file
- **2025-12-01 (Phase C.3)**: Relocated from `dbex.nanobrag_bridge` (lines 2103-2231) to `dbex.physics.forward` so gradcheck tests no longer import the bridge monolith; full docstring added with spec/finding references (RUNTIME-001, SCALE-001/002, GRADIENT-001, PHYSICS-LOSS-001, ARCH-FACTORY-001); TEST-ONLY warning added
