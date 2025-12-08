"""
Physics-based forward simulation utilities for gradient testing.

Leaf-node module: imports FROM external dependencies (torch, nanobrag_torch) but NOT from
dbex.nanobrag_* to avoid circular imports.

See docs/architecture/dbex/physics/forward.idl.md for full API & Contracts.

Functions in this module implement:
- Forward simulation with gradient preservation for DB-AT-010 gradcheck acceptance testing
- Tensor-valued parameter override mechanism for autograd testing
- ROI stacking and device/dtype management per spec-db-runtime.md

All functions preserve autograd graphs and are device-agnostic.

**TEST-ONLY**: Do not use in production LBFGS closures (use Stage A/B/C helpers instead).

References:
- docs/architecture/dbex/physics/forward.idl.md (canonical API contract)
- docs/spec-db-runtime.md §4.1 (gradient profile, RUNTIME-001)
- docs/spec-db-conformance.md:12-14 (DB-AT-010 acceptance)
- docs/development/testing_strategy.md:338-372 (gradcheck requirements)
- docs/pytorch_runtime_checklist.md:27-30 (NANOBRAGG_DISABLE_COMPILE=1)
- ARCH-ENGINE-002 (module-scope dependency declaration)

Findings applied:
- RUNTIME-001 (NANOBRAGG_DISABLE_COMPILE=1 for gradcheck)
- SCALE-001 (structure factors unscaled in grid)
- SCALE-002 (spot scale applied post-simulation)
- GRADIENT-001 (tensor-valued overrides preserve autograd)
- PHYSICS-LOSS-001 (variance-weighted loss)
- ARCH-ENGINE-002 (module-scope imports for Stage helpers)
"""

from __future__ import annotations
from typing import Optional
import numpy as np

# Optional torch/nanobrag_torch dependencies (ARCH-ENGINE-002)
# Module-scope imports ensure diagnostics/tests see import drift immediately
try:
    import torch
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models.detector import Detector as TorchDetector
    from nanobrag_torch.models.crystal import Crystal as TorchCrystal
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    torch = None  # type: ignore
    Simulator = None  # type: ignore
    TorchDetector = None  # type: ignore
    TorchCrystal = None  # type: ignore

# NOTE: dbex bridge helpers and refinement helpers CANNOT be imported at module scope
# because this is a LEAF MODULE and dbex.nanobrag_bridge imports from dbex.physics.forward,
# creating a circular dependency. Those imports must remain lazy (inside function body) per
# architecture constraint that physics/forward does NOT import from dbex.*


def _require_torch_forward() -> None:
    """
    Raise ImportError if torch/nanobrag_torch are unavailable.

    Preserves the same error message as legacy lazy imports for compatibility.
    """
    if not _TORCH_AVAILABLE:
        raise ImportError(
            "nanobrag_torch is required for simulate_forward_torch. "
            "Ensure torch and nanobrag_torch are installed."
        )


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
    crystal_overrides: Optional[dict] = None,
    detector_overrides: Optional[dict] = None,
    beam_overrides: Optional[dict] = None
) -> "torch.Tensor":
    """
    Run forward simulation returning torch tensor for gradient testing.

    See docs/architecture/dbex/physics/forward.idl.md §API for full contract.

    Similar to simulate_forward_once but preserves torch gradients by avoiding
    .detach().numpy() conversions. Designed for DB-AT-010 gradcheck acceptance
    testing with RUNTIME-001 (NANOBRAGG_DISABLE_COMPILE=1) enforcement.

    Args:
        inputs: RefinementInputs from prepare_refinement_inputs containing
                target, loss_mask, panel_slices, and global_scale_hint
        detector: dxtbx Detector object for geometry
        beam: dxtbx Beam object for wavelength/polarization
        crystal: dxtbx Crystal object for unit cell/orientation
        experiment: dxtbx Experiment object (for create_crystal_config)
        hkl_indices: Miller indices array from MTZ, shape (n_refl, 3)
        hkl_amplitudes: Structure factor amplitudes from MTZ, shape (n_refl,)
        spot_scale_override: Optional scale factor (default 1.0 if None)
        device: torch.device for simulation (default cpu)
        dtype: torch.dtype for computation (default float32, use float64 for gradcheck)
        crystal_overrides: Optional dict of tensor-valued crystal parameter overrides
                          for gradcheck. Supports keys: 'cell_a', 'cell_b', 'cell_c',
                          'cell_alpha', 'cell_beta', 'cell_gamma'. Applied AFTER config
                          creation to preserve gradient graph (GRADIENT-001). Tensors
                          must have requires_grad=True.
        detector_overrides: Optional dict of tensor-valued detector parameter overrides
                          for gradcheck. Supports keys: 'distance_mm'. Applied AFTER
                          config creation to preserve gradient graph (GRADIENT-001).
                          Tensors must have requires_grad=True.
        beam_overrides: Optional dict of tensor-valued beam parameter overrides
                          for gradcheck. Supports keys: 'wavelength_A'. Applied AFTER
                          config creation to preserve gradient graph (GRADIENT-001).
                          Tensors must have requires_grad=True.

    Returns:
        bragg_torch: Per-panel Bragg tensors [panel, slow, fast] as torch.Tensor
                     with SCALE-002 sqrt(spot_scale_override) applied differentiably

    Raises:
        ImportError: If nanobrag_torch is not available
        ValueError: If config creation fails or simulation errors

    Notes:
        - RUNTIME-001: Use with NANOBRAGG_DISABLE_COMPILE=1 for gradient tests
        - SCALE-001: Structure factors unscaled in grid
        - SCALE-002: sqrt(spot_scale) applied post-simulation as differentiable torch op
        - GRADIENT-001: crystal_overrides enables tensor-valued parameter injection without
                       .item()/.numpy() detaching, preserving autograd graph for gradcheck
        - Preserves gradient graph (no .detach() or .numpy() conversions)
        - Defaults to float32 but accepts float64 for gradcheck (per runtime checklist §2)
        - TEST-ONLY: Do not use in production LBFGS closures (use Stage A/B/C helpers instead)

    References:
        - docs/architecture/dbex/physics/forward.idl.md (canonical API contract)
        - docs/spec-db-core.md §§57-68 (variance-weighted chi-squared)
        - docs/spec-db-workflow.md §§30-45 (forward helper + telemetry expectations)
        - PHYSICS-LOSS-001 (shared variance-weighted loss)
        - ARCH-FACTORY-001 (forward helpers may use create_unified_simulator)
    """
    # Ensure optional dependencies are available (ARCH-ENGINE-002)
    _require_torch_forward()

    # Lazy imports of dbex bridge/refinement helpers (MUST remain lazy per leaf-module constraint)
    # This module is a LEAF and cannot import from dbex.* at module scope due to circular dependencies
    from dbex.nanobrag_bridge import build_structure_factor_grid
    from dbex.refinement.config_factories import (
        create_beam_config,
        create_crystal_config,
        create_detector_config
    )
    from dbex.refinement.helpers import create_unified_simulator

    # Default device and dtype per runtime checklist §2
    if device is None:
        device = torch.device('cpu')
    elif not isinstance(device, torch.device):
        device = torch.device(device)

    if dtype is None:
        dtype = torch.float32

    # Build structure factor grid (SCALE-001: unscaled)
    hkl_grid, hkl_metadata, asu_map = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device
    )

    # Ensure hkl_grid is correct dtype
    if hkl_grid.dtype != dtype:
        hkl_grid = hkl_grid.to(dtype=dtype)

    # Determine spot scale override (SCALE-002)
    if spot_scale_override is None:
        spot_scale_override = 1.0
    # Note: sqrt_spot_scale_tensor now computed per-panel by factory

    # Prepare configs (shared across panels where applicable)
    beam_config = create_beam_config(beam)

    # Apply beam overrides (post-creation pattern matching crystal_overrides)
    # This preserves gradient flow by assigning tensor values AFTER config creation
    if beam_overrides is not None and 'wavelength_A' in beam_overrides:
        beam_config.wavelength_A = beam_overrides['wavelength_A']

    # simulate_forward_torch doesn't use calibration, so apply_n_cells=True (default)
    # is fine for gradient testing; N_cells will be None anyway
    crystal_config, _ = create_crystal_config(crystal, experiment, crystal_overrides=crystal_overrides)

    # Apply crystal_overrides if provided (GRADIENT-001)
    # This allows tensor-valued parameters to flow through without .item() detaching
    if crystal_overrides is not None:
        # Get base unit cell parameters
        a, b, c, alpha, beta, gamma = crystal.get_unit_cell().parameters()

        # Override with tensor values (keep as torch tensors for autograd)
        if 'cell_a' in crystal_overrides:
            a = crystal_overrides['cell_a']
        if 'cell_b' in crystal_overrides:
            b = crystal_overrides['cell_b']
        if 'cell_c' in crystal_overrides:
            c = crystal_overrides['cell_c']
        if 'cell_alpha' in crystal_overrides:
            alpha = crystal_overrides['cell_alpha']
        if 'cell_beta' in crystal_overrides:
            beta = crystal_overrides['cell_beta']
        if 'cell_gamma' in crystal_overrides:
            gamma = crystal_overrides['cell_gamma']

        # Rebuild crystal_config with possibly-tensor unit cell params
        # CrystalConfig accepts numeric values, torch tensors should work
        crystal_config.cell_a = a
        crystal_config.cell_b = b
        crystal_config.cell_c = c
        crystal_config.cell_alpha = alpha
        crystal_config.cell_beta = beta
        crystal_config.cell_gamma = gamma

    # Run simulator per panel
    n_panels = len(detector)
    panel_shape = inputs.target.shape[1:]  # (slow, fast)
    bragg_panels = []

    for panel_id in range(n_panels):
        panel = detector[panel_id]

        # Create detector config for this panel
        detector_config = create_detector_config(
            panel=panel,
            beam=beam,
            trusted_mask=inputs.trusted_mask[panel_id]
        )

        # Apply detector overrides (post-creation pattern matching crystal_overrides)
        # This preserves gradient flow by assigning tensor values AFTER config creation
        if detector_overrides is not None and 'distance_mm' in detector_overrides:
            detector_config.distance_mm = detector_overrides['distance_mm']

        # Use unified factory (Phase B2a: eliminates manual mask/HKL/simulator setup)
        simulator, _, sqrt_scale_value, _ = create_unified_simulator(
            detector_config=detector_config,
            crystal_config=crystal_config,
            beam_config=beam_config,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            mask_array=detector_config.mask_array,
            spot_scale_override=spot_scale_override,
            device=device,
            dtype=dtype,  # simulate_forward_torch uses caller-provided dtype (float32 or float64)
            calibration_metadata=None
        )

        panel_output = simulator.run()  # Returns torch.Tensor on device

        # Apply sqrt(spot_scale_override) post-simulation (SCALE-002, differentiable)
        # Factory returns scalar, convert to tensor for differentiable scaling
        sqrt_scale_tensor = torch.tensor(sqrt_scale_value, dtype=dtype, device=device)
        panel_output_scaled = panel_output * sqrt_scale_tensor

        bragg_panels.append(panel_output_scaled)

    # Stack panels into single tensor [panel, slow, fast]
    bragg_torch = torch.stack(bragg_panels, dim=0)

    return bragg_torch
