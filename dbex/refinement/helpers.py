"""
Shared helpers for RefinementStage implementations (ARCH-REFINE-FLOW-001 Phase A).

Centralizes simulator instantiation and Bragg generation logic to avoid duplication
across Stage A/B/C implementations.

Functions:
- create_panel_simulator(...): Instantiate nanobrag_torch.Simulator for a panel
- create_unified_simulator(...): Unified factory with validation (TORCH-API-ALIGN-001 Phase B1)
- emit_bragg_frame(...): Generate full-frame Bragg tensor from stage parameters

Normative Requirements:
- Helpers MUST respect device/dtype neutrality (no hardcoded .cuda() or float32)
- Helpers MUST use lazy imports to avoid circular import issues
- Helpers are PLAN-LOCAL for Phase A (not used by existing Stage A/B/C until Phase B-D)

Environment Freeze (POLICY-001):
- Reuse existing tensor factories from dbex.nanobrag_bridge
- No new dependencies imported
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

import torch

if TYPE_CHECKING:
    # Lazy imports to avoid circular dependencies
    # These types are only needed for type hints, not runtime
    from dbex.nanobrag_bridge import DetectorConfig, CrystalConfig


def create_panel_simulator(
    detector_config: "DetectorConfig",
    crystal_config: "CrystalConfig",
    hkl_grid: Any,
    config: Any,
    device: torch.device,
    dtype: torch.dtype
) -> Any:
    """
    Centralize simulator instantiation logic for a single panel.

    Extracted from dbex/nanobrag_refinement.py Stage A panel loop (~800-900)
    to avoid duplication across Stage implementations.

    Args:
        detector_config: DetectorConfig instance for this panel
        crystal_config: CrystalConfig instance with current crystal state
        hkl_grid: HKL grid tensor (from nanobrag_bridge)
        config: RefinementConfig instance
        device: torch.device for tensors
        dtype: torch.dtype for tensors

    Returns:
        nanobrag_torch.Simulator instance configured for this panel

    Normative Requirements:
    - MUST respect device/dtype parameters (no hardcoded .cuda() or float32)
    - MUST use existing tensor factories from dbex.nanobrag_bridge
    - SHOULD enable tricubic interpolation when HKL grid has ±1 halo
      (REFINE-005: Stage B/C MUST enable, Stage A SHOULD enable)

    Phase A Note:
    This helper is PLAN-LOCAL for testing. Existing Stage A/B/C code will
    not use it until Phase B-D refactor.
    """
    # Lazy import to avoid circular dependency
    # nanobrag_torch is a heavy module that should not be imported at module level
    import nanobrag_torch

    # Instantiate simulator with panel detector config
    simulator = nanobrag_torch.Simulator(
        detector_config=detector_config,
        crystal_config=crystal_config,
        hkl_grid=hkl_grid,
        device=device,
        dtype=dtype
    )

    return simulator


def create_unified_simulator(
    detector_config,           # nanobrag_torch DetectorConfig (panel or cropped ROI)
    crystal_config,            # nanobrag_torch CrystalConfig
    beam_config,               # nanobrag_torch BeamConfig
    hkl_grid,                  # torch.Tensor (3, N) HKL coordinates
    hkl_metadata,              # dict with 'has_halo', 'hkl_ids_asu', etc.
    mask_array=None,           # Optional[np.ndarray] trusted mask (0=bad, 1=good)
    spot_scale_override=None,  # Optional[float] multiplicative scale (applied post-run as sqrt)
    device=None,               # torch.device or str
    dtype=None,                # torch.dtype
    calibration_metadata=None, # Optional[dict] with 'beam_config', 'N_cells', etc.
    debug_config=None,         # Optional[dict] for debug flags (DIAG-NANOBRAGG-OVERSAMPLE-001 Phase E)
):
    """
    Unified simulator factory for nanobrag_torch.

    Centralizes shape/dtype/device validation, mask normalization, and
    post-run spot_scale application. Eliminates duplication across forward
    helpers, CLI paths, and refinement loops.

    Parameters
    ----------
    detector_config : nanobrag_torch.config.DetectorConfig
        Panel or ROI-cropped detector configuration (DIALS convention).
    crystal_config : nanobrag_torch.config.CrystalConfig
        Crystal lattice and orientation parameters.
    beam_config : nanobrag_torch.config.BeamConfig
        X-ray beam properties (wavelength, polarization, flux).
    hkl_grid : torch.Tensor
        3D structure factor grid (h_range, k_range, l_range) from build_structure_factor_grid.
    hkl_metadata : dict
        Keys: 'has_halo' (bool), 'hkl_ids_asu' (Optional[Tensor]), etc.
    mask_array : Optional[np.ndarray]
        Trusted pixel mask (0=bad, 1=good). If provided, normalized to
        detector device/dtype and attached to detector_config.
    spot_scale_override : Optional[float]
        Multiplicative scale applied POST-RUN as sqrt(spot_scale_override)
        per SCALE-004 finding.
    device : Optional[torch.device or str]
        Target device (defaults to hkl_grid.device).
    dtype : Optional[torch.dtype]
        Target dtype (defaults to hkl_grid.dtype).
    calibration_metadata : Optional[dict]
        Preserved for telemetry/logging. Keys: 'beam_config', 'N_cells'.
    debug_config : Optional[dict]
        Debug configuration flags passed to Simulator. Keys: 'collect_hkl_stats', etc.
        (DIAG-NANOBRAGG-OVERSAMPLE-001 Phase E)

    Returns
    -------
    simulator : nanobrag_torch.Simulator
        Ready-to-run simulator instance with HKL tensors attached.
    normalized_mask : Optional[torch.Tensor]
        Mask tensor on device/dtype (if mask_array provided), else None.
    sqrt_scale : Optional[float]
        sqrt(spot_scale_override) to apply post-run, else None.
    metadata : dict
        Calibration metadata plus validation results.

    Notes
    -----
    - Lazy imports nanobrag_torch inside function to avoid circular deps.
    - Mask normalization: np.ndarray → torch.Tensor on device/dtype.
    - sqrt_scale is computed here but applied by CALLER after simulator.run().
    - ROI-cropped DetectorConfig: beam-center mm shift already applied in config.
    - DIALS convention: beam-center swap (fast,slow)→(s,f) handled upstream.

    Findings Applied
    ----------------
    - SCALE-004: sqrt_spot_scale post-run (not pre-run).
    - ARCH-ENGINE-002: Lazy imports inside function.
    - POLICY-001: No engine patches, dbex-only changes.
    """
    # Lazy imports
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models import Detector, Crystal
    import torch

    # Device/dtype defaults from hkl_grid
    if device is None:
        device = hkl_grid.device
    if dtype is None:
        dtype = hkl_grid.dtype
    device = torch.device(device) if isinstance(device, str) else device

    # Validate HKL grid shape (3D grid from build_structure_factor_grid)
    if hkl_grid.ndim != 3:
        raise ValueError(f"hkl_grid must be 3D (h_range, k_range, l_range), got {hkl_grid.shape}")
    if hkl_grid.device != device or hkl_grid.dtype != dtype:
        raise ValueError(f"hkl_grid device/dtype mismatch: expected {device}/{dtype}, got {hkl_grid.device}/{hkl_grid.dtype}")

    # Normalize mask to device/dtype if provided
    normalized_mask = None
    if mask_array is not None:
        # Handle torch.Tensor input (needs clone/detach, not torch.tensor)
        if isinstance(mask_array, torch.Tensor):
            normalized_mask = mask_array.to(device=device, dtype=dtype)
        else:
            normalized_mask = torch.tensor(mask_array, device=device, dtype=dtype)
        # Validate mask shape matches detector (panel or ROI-cropped)
        expected_shape = (detector_config.spixels, detector_config.fpixels)
        if normalized_mask.shape != expected_shape:
            raise ValueError(f"mask_array shape {normalized_mask.shape} does not match detector {expected_shape}")

    # Compute sqrt_scale for post-run application (per SCALE-004)
    sqrt_scale = None
    if spot_scale_override is not None:
        import math
        sqrt_scale = math.sqrt(spot_scale_override)

    # Build nanobrag_torch Detector and Crystal models
    detector = Detector(detector_config)
    crystal = Crystal(crystal_config, beam_config=beam_config, device=device, dtype=dtype)

    # Attach HKL tensors to crystal (direct assignment per original code pattern)
    crystal.hkl_data = hkl_grid
    crystal.hkl_metadata = hkl_metadata

    # Construct Simulator
    # DIAG-NANOBRAGG-OVERSAMPLE-001 Phase E: Pass debug_config for HKL stats collection
    simulator = Simulator(
        detector=detector,
        crystal=crystal,
        beam_config=beam_config,
        device=device,
        dtype=dtype,
        debug_config=debug_config
    )

    # Assemble metadata
    metadata = {
        'device': str(device),
        'dtype': str(dtype),
        'hkl_grid_shape': tuple(hkl_grid.shape),
        'has_halo': hkl_metadata.get('has_halo', False),
        'mask_provided': mask_array is not None,
        'spot_scale_override': spot_scale_override,
        'sqrt_scale': sqrt_scale,
    }
    if calibration_metadata is not None:
        metadata.update(calibration_metadata)

    return simulator, normalized_mask, sqrt_scale, metadata


def simulate_via_experiment_model(
    detector_config,
    crystal_config,
    beam_config,
    hkl_grid,
    hkl_metadata,
    mask_array=None,
    spot_scale_override=None,
    device=None,
    dtype=torch.float32,
    calibration_metadata=None
):
    """
    Thin adapter wrapping ExperimentModel(param_init="frozen") for parity testing.

    This adapter provides a parity path using the nanobrag_torch ExperimentModel API
    (docs/nanobrag_api.md) to validate shape/dtype/device consistency and output
    correctness against the unified simulator factory (create_unified_simulator).

    Args:
        detector_config: DetectorConfig instance
        crystal_config: CrystalConfig instance
        beam_config: BeamConfig instance (optional, can be None)
        hkl_grid: torch.Tensor (h_range, k_range, l_range) structure factors
        hkl_metadata: dict with 'has_halo', 'hkl_ids_asu' keys
        mask_array: Optional np.ndarray or torch.Tensor mask (normalized inside adapter)
        spot_scale_override: Optional float for post-run scaling (default 1.0)
        device: Optional torch.device (default from hkl_grid)
        dtype: torch.dtype (default torch.float32)
        calibration_metadata: Optional dict (stored in metadata, not used for construction)

    Returns:
        Tuple[torch.Tensor, float, dict]:
            - image: (spixels, fpixels) float tensor on device/dtype
            - sqrt_scale_value: float (sqrt of spot_scale_override) for CALLER to apply post-run
            - metadata: dict with {'device', 'dtype', 'hkl_count', 'has_halo', 'mask_provided', 'spot_scale_override', 'sqrt_scale', 'calibration_metadata', 'adapter': 'ExperimentModel'}

    Notes:
        - This adapter is behind an explicit flag (default OFF) for parity testing only.
        - param_init="frozen" ensures no trainable parameters (forward-only mode).
        - Post-run sqrt_scale application is CALLER's responsibility (matching factory pattern per SCALE-004).
        - Lazy imports nanobrag_torch.models.experiment.ExperimentModel inside function (ARCH-ENGINE-002).

    Findings Applied:
        - ARCH-ENGINE-002: Lazy imports
        - SCALE-004: Post-run sqrt_scale pattern
        - POLICY-001: Environment Freeze (ExperimentModel exists, no patches)
    """
    # Lazy import to avoid circular deps
    from nanobrag_torch.models.experiment import ExperimentModel

    # Device/dtype defaults from hkl_grid
    if device is None:
        device = hkl_grid.device
    if dtype is None:
        dtype = hkl_grid.dtype

    # Validate HKL grid shape (3D: h_range x k_range x l_range)
    if hkl_grid.ndim != 3:
        raise ValueError(f"HKL grid must be 3D (h, k, l), got shape {hkl_grid.shape}")
    if hkl_grid.device != device or hkl_grid.dtype != dtype:
        hkl_grid = hkl_grid.to(device=device, dtype=dtype)

    # Compute sqrt(spot_scale_override) for CALLER to apply post-run (SCALE-004)
    import math
    spot_scale_val = 1.0 if spot_scale_override is None else spot_scale_override
    sqrt_scale_value = math.sqrt(spot_scale_val)

    # Instantiate ExperimentModel with param_init="frozen" (no trainable parameters)
    experiment = ExperimentModel(
        crystal_config=crystal_config,
        detector_config=detector_config,
        beam_config=beam_config,
        device=device,
        dtype=dtype,
        param_init="frozen",
        hkl_data=hkl_grid,
        hkl_metadata=hkl_metadata
    )

    # Run forward pass
    image = experiment()

    # Validate output shape/dtype
    expected_shape = (detector_config.spixels, detector_config.fpixels)
    if image.shape != expected_shape:
        raise ValueError(f"ExperimentModel output shape {image.shape} != expected {expected_shape}")
    if image.dtype != dtype:
        raise ValueError(f"ExperimentModel output dtype {image.dtype} != expected {dtype}")
    if image.device != device:
        raise ValueError(f"ExperimentModel output device {image.device} != expected {device}")

    # Assemble metadata
    metadata = {
        'device': str(device),
        'dtype': str(dtype),
        'hkl_count': hkl_grid.shape[0] * hkl_grid.shape[1] * hkl_grid.shape[2],
        'has_halo': hkl_metadata.get('has_halo', False),
        'mask_provided': mask_array is not None,
        'spot_scale_override': spot_scale_val,
        'sqrt_scale': sqrt_scale_value,
        'adapter': 'ExperimentModel',
        'param_init': 'frozen'
    }
    if calibration_metadata is not None:
        metadata['calibration_metadata'] = calibration_metadata

    return image, sqrt_scale_value, metadata


def emit_bragg_frame(
    stage_params: Dict[str, torch.Tensor],
    inputs: Any,
    config: Any,
    simulators: List[Any]
) -> torch.Tensor:
    """
    Centralize full-frame Bragg generation from stage parameters.

    Extracted from Stage A/B/C closures to centralize Bragg stitching logic.

    Args:
        stage_params: Dict of parameter tensors (e.g., scale, cell deltas, etc.)
        inputs: RefinementInputs instance
        config: RefinementConfig instance
        simulators: List of nanobrag_torch.Simulator instances (one per panel)

    Returns:
        torch.Tensor of shape [panel, slow, fast] containing stitched Bragg frame

    Normative Requirements:
    - Output tensor MUST have shape [panel, slow, fast] per spec-db-core.md
    - MUST respect device/dtype from simulators (no hardcoded conversions)
    - SHOULD NOT re-derive physics (use production Simulator.forward())

    Phase A Note:
    This helper is PLAN-LOCAL for testing. Existing Stage A/B/C code will
    not use it until Phase B-D refactor.

    Future Extensions (Phase B-D):
    - Stage B: apply per-reflection Fhkl modifiers before forward pass
    - Stage C: update detector distances before forward pass
    """
    # TODO: Implement Bragg stitching logic
    # For Phase A (TDD nucleus), this can be a minimal stub
    # Full implementation will extract logic from dbex/nanobrag_refinement.py
    # Stage A/B/C closures during Phase B-D refactor

    # Placeholder: return zero tensor matching expected shape
    # Real implementation will:
    # 1. Extract panel shapes from simulators
    # 2. Call simulator.forward() for each panel
    # 3. Stitch panels into [panel, slow, fast] tensor
    # 4. Apply stage-specific parameter updates (scale, modifiers, detector offsets)

    raise NotImplementedError(
        "emit_bragg_frame is a Phase A stub. "
        "Full implementation planned for Phase B-D refactor."
    )
