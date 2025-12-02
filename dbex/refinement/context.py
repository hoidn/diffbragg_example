# dbex/refinement/context.py
"""
RefinementContext and JobContext dataclasses for typed refinement inputs.

Replaces ad-hoc dicts passed through RefinementEngine and Stage wrappers
with typed objects per ARCH-REFINE-001 Phase B.1/B.2.

Normative Requirements:
- docs/spec-db-workflow.md §7 (Refinement Protocol Architecture)
- docs/spec-db-workflow.md §§32-41 (Calibration & Unit Conventions)
- docs/config_crosswalk.md §3 (Config Mapping and Refinement Crosswalk)
- docs/spec-db-core.md (geometry/HKL contracts)
- docs/architecture.md (IDL-style contracts)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch


@dataclass
class RefinementContext:
    """
    Typed container for shared refinement state across Stage A/B/C.

    All stages receive the same RefinementContext instance, ensuring
    consistent geometry/HKL/baseline state throughout the refinement flow.

    Attributes:
        refinement_inputs: RefinementInputs dataclass (target, loss_mask, panel_slices,
                          trusted_mask, sigma_readout, target_representation, global_scale_hint)
        detector: dxtbx Detector object (panel geometry)
        beam: dxtbx Beam object (wavelength, polarization, direction)
        crystal: dxtbx Crystal object (unit cell, orientation)
        hkl_grid: torch.Tensor structure factor grid [h, k, l] with complex |F|
        hkl_metadata: Dict with grid dimensions (nabc_grid, default_F, has_halo, etc.)
        baseline_crystal: Optional baseline dxtbx Crystal for misset extraction
                         (used when crystal is perturbed; Stage A computes delta misset)
        baseline_detector: Optional baseline dxtbx Detector for Stage C offset reference
                          (required when Stage C is enabled)
        asu_map: Optional torch.Tensor ASU mapping tensor (same shape as hkl_grid, dtype int32)
                with ASU indices or -1 for unmapped reflections. When provided by JobContext,
                Stage B per-reflection mode reuses this tensor instead of calling compute_hkl_asu_map.
        hkl_indices_grid: Optional np.ndarray Miller indices grid [h_range, k_range, l_range, 3]
                         containing (h, k, l) tuples. When provided, Stage B skips reconstruction
                         from hkl_metadata bounds.
        halo_mask: Optional np.ndarray boolean mask [h_range, k_range, l_range] marking halo padding
                  cells (True=halo, False=data). Stage B passes this to compute_hkl_asu_map
                  when calling the cctbx fallback path.
        extras: Dict[str, Any] for future extensions (job metadata, provenance, etc.)

    Normative Dependencies (Transitive):
    - refinement_inputs.target: Prepared per spec-db-core.md:20 ([panel, slow, fast])
    - refinement_inputs.loss_mask: (background >= 0) ∧ trusted_mask per spec-db-core.md:55
    - detector: dxtbx Detector with square pixels per config_crosswalk.md:30
    - beam: dxtbx Beam with wavelength and polarization per config_crosswalk.md:65-70
    - crystal: dxtbx Crystal with unit cell and orientation per config_crosswalk.md:75-80
    - hkl_grid: Structure factors per spec-db-core.md:85-90 (refined MTZ preferred)
    - hkl_metadata['has_halo']: Stage B/C require halo-padded grid per spec-db-workflow.md:53-54
    - asu_map: Optional ASU mapping from build_structure_factor_grid per REFINE-005
    - hkl_indices_grid: Optional Miller indices grid for Stage B per-reflection mode
    - halo_mask: Optional halo padding mask for cctbx ASU mapping fallback

    IDL Contract Reference:
    - docs/architecture.md (modular structure)
    - docs/spec-db-workflow.md:48-84 (Refinement Protocol Architecture)
    - docs/architecture/dbex/refinement/context.idl.md (detailed field contracts)

    Provenance:
    - ARCH-REFINE-001 Phase B.3: Thread CLI-built HKL halo + ASU metadata into RefinementContext
      so Stage B/C consume the same tensors without recomputing (REFINE-005, REFINE-010)
    """
    refinement_inputs: Any  # RefinementInputs from dbex.nanobrag_bridge
    detector: Any  # dxtbx Detector object
    beam: Any  # dxtbx Beam object
    crystal: Any  # dxtbx Crystal object
    hkl_grid: torch.Tensor  # [h, k, l] complex structure factor grid
    hkl_metadata: Dict[str, Any]  # nabc_grid, default_F, has_halo, etc.
    baseline_crystal: Optional[Any] = None  # baseline dxtbx Crystal (for misset extraction)
    baseline_detector: Optional[Any] = None  # baseline dxtbx Detector (for Stage C offsets)
    asu_map: Optional[torch.Tensor] = None  # ASU mapping tensor from build_structure_factor_grid
    hkl_indices_grid: Optional[np.ndarray] = None  # Miller indices grid [h_range, k_range, l_range, 3]
    halo_mask: Optional[np.ndarray] = None  # Halo padding mask [h_range, k_range, l_range]
    extras: Dict[str, Any] = field(default_factory=dict)  # Future extensions


def build_refinement_context(
    refinement_inputs,
    detector,
    beam,
    crystal,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict[str, Any],
    baseline_crystal=None,
    baseline_detector=None,
    asu_map: Optional[torch.Tensor] = None,
    hkl_indices_grid: Optional[np.ndarray] = None,
    halo_mask: Optional[np.ndarray] = None,
    extras: Optional[Dict[str, Any]] = None,
    job_context: Optional['JobContext'] = None,
) -> RefinementContext:
    """
    Build a RefinementContext from raw inputs, validating tensor/device expectations.

    Args:
        refinement_inputs: RefinementInputs dataclass (target, loss_mask, panel_slices, etc.)
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object
        hkl_grid: torch.Tensor structure factor grid [h, k, l]
        hkl_metadata: Dict with grid dimensions (nabc_grid, default_F, has_halo, etc.)
        baseline_crystal: Optional baseline dxtbx Crystal for misset extraction
        baseline_detector: Optional baseline dxtbx Detector for Stage C offsets
        asu_map: Optional torch.Tensor ASU mapping from build_structure_factor_grid
                (same shape as hkl_grid, dtype int32). If None and job_context is provided,
                will be copied from job_context.asu_map.
        hkl_indices_grid: Optional np.ndarray Miller indices grid [h_range, k_range, l_range, 3].
                         If None and job_context is provided with extras['hkl_indices_grid'],
                         will be copied from there.
        halo_mask: Optional np.ndarray boolean mask [h_range, k_range, l_range] marking halo cells.
                  If None and job_context is provided with extras['halo_mask'], will be copied.
        extras: Optional dict for future extensions (job metadata, provenance, etc.)
        job_context: Optional JobContext to pull asu_map/hkl_indices_grid/halo_mask from when
                    not explicitly provided (ARCH-REFINE-001 Phase B.3)

    Returns:
        RefinementContext instance with validated inputs

    Raises:
        ValueError: If hkl_grid is not a torch.Tensor or hkl_metadata is missing required keys
        TypeError: If asu_map/hkl_indices_grid/halo_mask have wrong types

    Normative Requirements:
    - hkl_grid must be a torch.Tensor per spec-db-core.md:85-90
    - hkl_metadata must contain 'has_halo' key per spec-db-workflow.md:53-54
    - asu_map (if provided) must be torch.Tensor with same shape as hkl_grid per REFINE-005
    - hkl_indices_grid (if provided) must be np.ndarray shape [h_range, k_range, l_range, 3]
    - halo_mask (if provided) must be np.ndarray shape [h_range, k_range, l_range] with dtype bool
    - Device/dtype neutrality: this builder does NOT enforce specific device/dtype;
      stages are responsible for tensor device/dtype management per pytorch_runtime_checklist.md

    Provenance:
    - ARCH-REFINE-001 Phase B.1: Replace ad-hoc dict plumbing with typed context
    - ARCH-REFINE-001 Phase B.3: Thread CLI-built HKL halo + ASU metadata into RefinementContext
    - docs/spec-db-workflow.md:48-84: Refinement Protocol Architecture
    - docs/architecture.md: IDL-style contracts for all components
    """
    # Validate hkl_grid is a tensor
    if not isinstance(hkl_grid, torch.Tensor):
        raise ValueError(
            f"hkl_grid must be torch.Tensor, got {type(hkl_grid).__name__}. "
            "Per spec-db-core.md:85-90, structure factors must be provided as tensors."
        )

    # Validate hkl_metadata contains required keys
    # Only validate 'has_halo' key exists (required for Stage B/C per spec-db-workflow.md:53-54)
    # Other keys vary based on implementation details
    if 'has_halo' not in hkl_metadata:
        raise ValueError(
            "hkl_metadata missing required key 'has_halo'. "
            "Per spec-db-workflow.md:53-54, Stage B/C require halo-padded grids."
        )

    # Validate refinement_inputs is not None (sanity check)
    if refinement_inputs is None:
        raise ValueError(
            "refinement_inputs must not be None. "
            "Per spec-db-core.md:20, target/loss_mask/panel_slices are required."
        )

    # Copy asu_map from job_context if not explicitly provided (ARCH-REFINE-001 Phase B.3)
    if asu_map is None and job_context is not None and job_context.asu_map is not None:
        # Convert np.ndarray to torch.Tensor if needed (JobContext stores np.ndarray)
        if isinstance(job_context.asu_map, np.ndarray):
            asu_map = torch.from_numpy(job_context.asu_map)
        else:
            asu_map = job_context.asu_map

    # Copy hkl_indices_grid from job_context.extras if not explicitly provided
    if hkl_indices_grid is None and job_context is not None:
        hkl_indices_grid = job_context.extras.get('hkl_indices_grid')

    # Copy halo_mask from job_context.extras if not explicitly provided
    if halo_mask is None and job_context is not None:
        halo_mask = job_context.extras.get('halo_mask')

    # Validate asu_map type and shape if provided
    if asu_map is not None:
        if not isinstance(asu_map, torch.Tensor):
            raise TypeError(
                f"asu_map must be torch.Tensor if provided, got {type(asu_map).__name__}. "
                "Per REFINE-005, ASU mapping must be a tensor for device neutrality."
            )
        # Validate shape matches hkl_grid (allow shape mismatch to fail later with clear error)
        if asu_map.shape != hkl_grid.shape:
            raise ValueError(
                f"asu_map shape {asu_map.shape} must match hkl_grid shape {hkl_grid.shape}. "
                "Per REFINE-005, ASU mapping must cover the entire HKL grid."
            )

    # Validate hkl_indices_grid type if provided
    if hkl_indices_grid is not None and not isinstance(hkl_indices_grid, np.ndarray):
        raise TypeError(
            f"hkl_indices_grid must be np.ndarray if provided, got {type(hkl_indices_grid).__name__}."
        )

    # Validate halo_mask type if provided
    if halo_mask is not None and not isinstance(halo_mask, np.ndarray):
        raise TypeError(
            f"halo_mask must be np.ndarray if provided, got {type(halo_mask).__name__}."
        )

    # Build context with all fields
    return RefinementContext(
        refinement_inputs=refinement_inputs,
        detector=detector,
        beam=beam,
        crystal=crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,
        asu_map=asu_map,
        hkl_indices_grid=hkl_indices_grid,
        halo_mask=halo_mask,
        extras=extras if extras is not None else {},
    )


@dataclass
class JobContext:
    """
    Typed container for job-level metadata and calibration state.

    Encapsulates CLI args, DataLoad handle, calibration metadata, sigma provenance,
    HKL metadata/ASU map, and RefinementConfig so stages can access consistent
    job metadata without recomputing or relying on global state.

    Attributes:
        cli_args: argparse.Namespace from CLI (or equivalent dict for programmatic calls)
        dataload: DataLoad object with experiment, detector, beam, crystal, reflections
        calibration_metadata: Optional dict from torch_config.json with spot_scale_override,
                            beam flux/exposure/beamsize, N_cells (or None if not provided)
        sigma_provenance: str describing sigma_readout source ("cli_override", "calibrated_map",
                         "external_lookup", etc.) per spec-db-core.md:32-68
        sigma_reference_value: float scalar sigma_readout reference in target units
                              (after ADU→photon conversion if applicable)
        refinement_config: RefinementConfig instance (device, dtype, sigma_floor, stage flags, etc.)
        hkl_metadata: Dict with HKL grid dimensions (nabc_grid, default_F, has_halo, etc.)
                     from build_structure_factor_grid
        asu_map: Optional np.ndarray ASU mapping for Stage B per-reflection mode
                (or None if not computed)
        spot_scale_override: float spot scale override applied post-simulation (SCALE-002)
        hkl_source: str HKL source provenance ("refined" or "raw")
        hkl_path: Optional str path to MTZ file used for structure factors
        extras: Dict[str, Any] for future extensions (telemetry sinks, output paths, etc.)

    Normative Dependencies (Transitive):
    - cli_args: CLI parser output per refine_one.py create_parser()
    - dataload: DataLoad from load_dataload() with experiment/detector/beam/crystal
    - calibration_metadata: Optional dict from load_calibration_metadata() per spec-db-workflow.md:34-44
    - sigma_provenance/reference_value: From _resolve_sigma_readout() per spec-db-core.md:32-68
    - refinement_config: RefinementConfig with device/dtype/sigma_floor per spec-db-workflow.md:36-42
    - hkl_metadata: From build_structure_factor_grid() per spec-db-core.md:85-90
    - asu_map: Optional ASU mapping for Stage B per-reflection mode
    - spot_scale_override: Calibration or CLI override per spec-db-workflow.md:34-44
    - hkl_source/hkl_path: HKL provenance for telemetry per spec-db-workflow.md:43-46

    IDL Contract Reference:
    - docs/spec-db-workflow.md:48-84 (Refinement Protocol Architecture)
    - docs/spec-db-workflow.md:32-47 (Calibration & Unit Conventions)
    - docs/config_crosswalk.md (Config Mapping)
    - docs/architecture.md (modular structure)

    Provenance:
    - ARCH-REFINE-001 Phase B.2: Introduce JobContext to replace ad-hoc globals
    - PHYSICS-LOSS-001: Sigma provenance and reference values must travel with the job
    """
    cli_args: Any  # argparse.Namespace or dict
    dataload: Any  # DataLoad object from dbex.load_dataload
    calibration_metadata: Optional[Dict[str, Any]]  # torch_config.json payload or None
    sigma_provenance: str  # "cli_override", "calibrated_map", "external_lookup", etc.
    sigma_reference_value: float  # sigma_readout reference in target units
    refinement_config: Any  # RefinementConfig from dbex.nanobrag_refinement
    hkl_metadata: Dict[str, Any]  # nabc_grid, default_F, has_halo, etc.
    asu_map: Optional[np.ndarray] = None  # ASU mapping for Stage B per-reflection mode
    spot_scale_override: float = 1.0  # spot scale override (SCALE-002)
    hkl_source: str = "raw"  # "refined" or "raw"
    hkl_path: Optional[str] = None  # MTZ file path
    extras: Dict[str, Any] = field(default_factory=dict)  # Future extensions


def build_job_context(
    cli_args,
    dataload,
    calibration_metadata: Optional[Dict[str, Any]],
    sigma_provenance: str,
    sigma_reference_value: float,
    refinement_config,
    hkl_metadata: Dict[str, Any],
    asu_map: Optional[np.ndarray] = None,
    spot_scale_override: float = 1.0,
    hkl_source: str = "raw",
    hkl_path: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> JobContext:
    """
    Build a JobContext from CLI args, DataLoad, and calibration/sigma metadata.

    Args:
        cli_args: argparse.Namespace from CLI (or dict for programmatic calls)
        dataload: DataLoad object with experiment/detector/beam/crystal
        calibration_metadata: Optional dict from torch_config.json (spot_scale_override,
                            beam flux/exposure/beamsize, N_cells) or None
        sigma_provenance: str describing sigma_readout source per spec-db-core.md:32-68
        sigma_reference_value: float scalar sigma_readout reference in target units
        refinement_config: RefinementConfig instance
        hkl_metadata: Dict with HKL grid dimensions from build_structure_factor_grid
        asu_map: Optional np.ndarray ASU mapping for Stage B per-reflection mode
        spot_scale_override: float spot scale override (SCALE-002)
        hkl_source: str HKL source provenance ("refined" or "raw")
        hkl_path: Optional str path to MTZ file
        extras: Optional dict for future extensions (telemetry sinks, output paths, etc.)

    Returns:
        JobContext instance with validated inputs

    Raises:
        ValueError: If required fields are invalid (negative sigma_reference_value, empty
                   sigma_provenance, missing hkl_metadata keys, etc.)

    Normative Requirements:
    - sigma_reference_value must be strictly positive per spec-db-core.md:32-68
    - sigma_provenance must be non-empty and describe the readout noise source
    - hkl_metadata must contain 'has_halo' key per spec-db-workflow.md:53-54
    - spot_scale_override must be strictly positive (applied post-simulation per SCALE-002)
    - hkl_source must be "refined" or "raw" per spec-db-workflow.md:43-46
    - Device/dtype neutrality: this builder does NOT enforce specific device/dtype;
      stages are responsible for tensor device/dtype management per pytorch_runtime_checklist.md

    Provenance:
    - ARCH-REFINE-001 Phase B.2: Introduce JobContext to replace ad-hoc globals
    - docs/spec-db-workflow.md:32-47: Calibration & Unit Conventions
    - docs/config_crosswalk.md §3: Config Mapping and Refinement Crosswalk
    - PHYSICS-LOSS-001: Sigma provenance must travel with the job
    """
    # Validate sigma_reference_value is strictly positive
    if sigma_reference_value <= 0:
        raise ValueError(
            f"sigma_reference_value must be strictly positive (got {sigma_reference_value}). "
            "Per spec-db-core.md:32-68, variance weights require positive readout noise."
        )

    # Validate sigma_provenance is non-empty
    if not sigma_provenance or not sigma_provenance.strip():
        raise ValueError(
            "sigma_provenance must be non-empty. "
            "Per PHYSICS-LOSS-001, sigma source must be documented for telemetry."
        )

    # Validate hkl_metadata contains required keys (same as RefinementContext)
    if 'has_halo' not in hkl_metadata:
        raise ValueError(
            "hkl_metadata missing required key 'has_halo'. "
            "Per spec-db-workflow.md:53-54, Stage B/C require halo-padded grids."
        )

    # Validate spot_scale_override is strictly positive
    if spot_scale_override <= 0:
        raise ValueError(
            f"spot_scale_override must be strictly positive (got {spot_scale_override}). "
            "Per SCALE-002, spot scale is applied post-simulation and must be > 0."
        )

    # Validate hkl_source is "refined" or "raw"
    if hkl_source not in ("refined", "raw"):
        raise ValueError(
            f"hkl_source must be 'refined' or 'raw' (got '{hkl_source}'). "
            "Per spec-db-workflow.md:43-46, HKL provenance must be documented."
        )

    # Validate dataload is not None (sanity check)
    if dataload is None:
        raise ValueError(
            "dataload must not be None. "
            "JobContext requires DataLoad with experiment/detector/beam/crystal."
        )

    # Validate refinement_config is not None (sanity check)
    if refinement_config is None:
        raise ValueError(
            "refinement_config must not be None. "
            "JobContext requires RefinementConfig with device/dtype/sigma_floor."
        )

    # Build JobContext with all fields
    return JobContext(
        cli_args=cli_args,
        dataload=dataload,
        calibration_metadata=calibration_metadata,
        sigma_provenance=sigma_provenance,
        sigma_reference_value=sigma_reference_value,
        refinement_config=refinement_config,
        hkl_metadata=hkl_metadata,
        asu_map=asu_map,
        spot_scale_override=spot_scale_override,
        hkl_source=hkl_source,
        hkl_path=hkl_path,
        extras=extras if extras is not None else {},
    )


@dataclass
class RefinementSharedContext:
    """
    Shared refinement state for Stage A/B/C LBFGS closures.

    Replaces 11-parameter data clump passed to Stage closure builders (Phase A.2)
    and now passed to StageA/B/C._build_lbfgs_closure methods (Phase B.2).

    Per ARCH-STAGE-CONTEXT-001, this dataclass wraps:
    - Geometry objects (detector, beam, crystal) from dxtbx
    - RefinementInputs (target, loss_mask, panel_slices, trusted_mask, sigma_readout)
    - HKL grid and metadata
    - Configuration (device, dtype, RefinementConfig)
    - Warm-cache infrastructure (sigma_floor_sq_cache)
    - Baseline references (baseline_crystal for misset extraction)

    Attributes:
        crystal: dxtbx Crystal object (unit cell, orientation)
        detector: dxtbx Detector object (panel geometry)
        beam: dxtbx Beam object (wavelength, polarization, direction)
        inputs: RefinementInputs dataclass (target, loss_mask, panel_slices,
               trusted_mask, sigma_readout, target_representation, global_scale_hint)
        hkl_grid: torch.Tensor structure factor grid [h, k, l] with complex |F|
        hkl_metadata: Dict with grid dimensions (nabc_grid, default_F, has_halo, etc.)
        config: RefinementConfig instance (device, dtype, optimizer params, stage flags)
        sigma_floor_sq_cache: Dict for cached sigma floor tensors (warmup optimization)
        device: torch.device for tensor allocation
        dtype: torch.dtype for tensor allocation
        baseline_crystal: Optional baseline dxtbx Crystal for misset extraction
        baseline_detector: Optional baseline dxtbx Detector for Stage C distance offsets

    Normative Dependencies (Transitive):
    - crystal/detector/beam: dxtbx objects per config_crosswalk.md
    - inputs: RefinementInputs per spec-db-core.md:20-68
    - hkl_grid: Structure factors per spec-db-core.md:85-90
    - config: RefinementConfig per spec-db-workflow.md:36-42
    - sigma_floor_sq_cache: Warm-cache dict populated by _get_sigma_floor_sq_tensor
      (dbex/refinement/stage_a_impl.py)
    - device/dtype: PyTorch device/dtype neutrality per pytorch_runtime_checklist.md

    IDL Contract Reference:
    - docs/architecture.md (modular structure)
    - docs/spec-db-workflow.md:48-84 (Refinement Protocol Architecture)
    - ARCH-STAGE-CONTEXT-001: Stage helper dataclass refactoring

    Provenance:
    - ARCH-STAGE-CONTEXT-001 Phase A.1: Introduce typed context to replace
      11-parameter data clump in Stage A/B/C LBFGS closure builders
    """
    crystal: Any  # dxtbx Crystal object
    detector: Any  # dxtbx Detector object
    beam: Any  # dxtbx Beam object
    inputs: Any  # RefinementInputs from dbex.nanobrag_bridge
    hkl_grid: torch.Tensor  # [h, k, l] complex structure factor grid
    hkl_metadata: Dict[str, Any]  # nabc_grid, default_F, has_halo, etc.
    config: Any  # RefinementConfig from dbex.nanobrag_refinement
    sigma_floor_sq_cache: Dict[str, torch.Tensor]  # Warm-cache dict
    device: Any  # torch.device
    dtype: Any  # torch.dtype
    baseline_crystal: Optional[Any] = None  # baseline dxtbx Crystal
    baseline_detector: Optional[Any] = None  # baseline dxtbx Detector (Stage C distance offsets)

    @classmethod
    def from_inputs(
        cls,
        crystal,
        detector,
        beam,
        inputs,
        hkl_grid: torch.Tensor,
        hkl_metadata: Dict[str, Any],
        config,
        device,
        dtype,
        baseline_crystal=None,
        baseline_detector=None,
        sigma_floor_sq_cache: Optional[Dict] = None,
    ) -> 'RefinementSharedContext':
        """
        Build RefinementSharedContext from raw inputs.

        Args:
            crystal: dxtbx Crystal object
            detector: dxtbx Detector object
            beam: dxtbx Beam object
            inputs: RefinementInputs dataclass
            hkl_grid: torch.Tensor structure factor grid
            hkl_metadata: Dict with grid dimensions
            config: RefinementConfig instance
            device: torch.device
            dtype: torch.dtype
            baseline_crystal: Optional baseline dxtbx Crystal
            baseline_detector: Optional baseline dxtbx Detector (Stage C distance offsets)
            sigma_floor_sq_cache: Optional warm-cache dict (defaults to empty dict)

        Returns:
            RefinementSharedContext instance
        """
        if sigma_floor_sq_cache is None:
            sigma_floor_sq_cache = {}

        return cls(
            crystal=crystal,
            detector=detector,
            beam=beam,
            inputs=inputs,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            config=config,
            sigma_floor_sq_cache=sigma_floor_sq_cache,
            device=device,
            dtype=dtype,
            baseline_crystal=baseline_crystal,
            baseline_detector=baseline_detector,
        )


@dataclass
class StageATelemetryState:
    """
    Mutable telemetry accumulators for Stage A LBFGS refinement.

    Replaces the 'telemetry_state' dict passed through _build_stage_a_lbfgs_closure.
    Lists accumulate traces during optimization; counters track perf/validation stats.

    Per ARCH-STAGE-CONTEXT-001 Phase B.3.1, this dataclass owns every accumulator currently
    in the telemetry_state dict: iteration counter, dual metric traces (chi²/MSE), perf counters,
    variance-floor stats, sigma_floor tensor, telemetry_step_counter, lifecycle logs, best snapshots,
    and optional panel_loss_diag for PERF-WARM-SIM-001 diagnostics.

    Attributes:
        iteration_count: Mutable list wrapping iteration counter for closure capture (e.g., [0])
        loss_trace_sample: List of floats recording loss on sampled ROI subset per closure eval
        loss_trace_full: List of floats recording loss on full validation set
        best_loss_full: List of floats tracking best full-validation loss seen so far
        best_params_snapshot: List containing parameter snapshots at best loss (mutable container)
        chi_squared_trace_sample: List of floats recording chi² on sampled subset (PHYSICS-LOSS-001)
        chi_squared_trace_full: List of floats recording chi² on full validation set
        chi_squared_best: Tuple of (float, int) tracking best chi² and iteration
        masked_mse_trace_sample: List of floats recording masked MSE on sampled subset
        masked_mse_trace_full: List of floats recording masked MSE on full validation set
        masked_mse_best: Tuple of (float, int) tracking best masked MSE and iteration
        perf_closure_evals: Mutable list wrapping closure eval counter (e.g., [0])
        perf_validation_runs: Mutable list wrapping validation run counter (e.g., [0])
        perf_forward_times_ms: List of floats recording forward pass times in milliseconds
        variance_floor_clamped_pixels: Mutable list wrapping clamped pixel counter (e.g., [0])
        variance_floor_masked_pixels: Mutable list wrapping masked pixel counter (e.g., [0])
        sigma_floor_sq_tensor: Cached sigma_floor^2 tensor (PHYSICS-LOSS-002)
        telemetry_step_counter: Mutable list wrapping telemetry step counter (e.g., [0])
        u_matrix_lifecycle_log: List tracking U-matrix checksum per closure call (TORCH-GEOMETRY-CONVERGENCE-001)
        a_star_lifecycle_log: List tracking A* reconstruction per closure call
        panel_loss_diag: Optional list for per-panel diagnostics (PERF-WARM-SIM-001), None if disabled

    Normative Dependencies:
    - Telemetry lists accumulate during LBFGS optimization per spec-db-workflow.md:48-84
    - Final telemetry dict assembled in stage_a.py::StageA.run and returned to engine
    - Variance floor stats per spec-db-core.md:57-68 (variance-weighted loss)
    - Dual metric tracking (chi² + masked MSE) per PHYSICS-LOSS-001
    - Lifecycle logs per TORCH-GEOMETRY-CONVERGENCE-001 Phase B4

    IDL Contract Reference:
    - docs/spec-db-workflow.md:48-84 (Refinement Protocol Architecture)
    - ARCH-STAGE-CONTEXT-001: Telemetry dataclass refactoring

    Provenance:
    - ARCH-STAGE-CONTEXT-001 Phase A.1: Initial stub with basic fields
    - ARCH-STAGE-CONTEXT-001 Phase B.3.1: Expanded to own all telemetry_state dict keys
    """
    # Mutable counters (lists for closure capture)
    iteration_count: List[int] = field(default_factory=lambda: [0])
    perf_closure_evals: List[int] = field(default_factory=lambda: [0])
    perf_validation_runs: List[int] = field(default_factory=lambda: [0])
    variance_floor_clamped_pixels: List[int] = field(default_factory=lambda: [0])
    variance_floor_masked_pixels: List[int] = field(default_factory=lambda: [0])
    telemetry_step_counter: List[int] = field(default_factory=lambda: [0])

    # Loss traces (floats)
    loss_trace_sample: List[float] = field(default_factory=list)
    loss_trace_full: List[float] = field(default_factory=list)
    best_loss_full: List[float] = field(default_factory=list)

    # Chi-squared traces (PHYSICS-LOSS-001)
    chi_squared_trace_sample: List[float] = field(default_factory=list)
    chi_squared_trace_full: List[float] = field(default_factory=list)
    chi_squared_best: List[float] = field(default_factory=lambda: [float('inf'), -1])

    # Masked MSE traces (PHYSICS-LOSS-001)
    masked_mse_trace_sample: List[float] = field(default_factory=list)
    masked_mse_trace_full: List[float] = field(default_factory=list)
    masked_mse_best: List[float] = field(default_factory=lambda: [float('inf'), -1])

    # Performance timing
    perf_forward_times_ms: List[float] = field(default_factory=list)

    # Best parameter snapshot (mutable container)
    best_params_snapshot: List[Any] = field(default_factory=list)

    # Lifecycle logs (TORCH-GEOMETRY-CONVERGENCE-001 Phase B4)
    u_matrix_lifecycle_log: List[Any] = field(default_factory=list)
    a_star_lifecycle_log: List[Any] = field(default_factory=list)

    # Variance floor tensor (cached, not a trace)
    sigma_floor_sq_tensor: Optional[Any] = None

    # Optional panel diagnostics (PERF-WARM-SIM-001 Phase D.4)
    panel_loss_diag: Optional[List[Any]] = None


@dataclass
class StageBTelemetryState:
    """
    Mutable telemetry accumulators for Stage B LBFGS refinement.

    Replaces the 'telemetry_state' dict passed through StageB._build_lbfgs_closure.
    Lists accumulate traces during optimization; counters track perf/validation stats.

    Per ARCH-STAGE-CONTEXT-001 Phase B.3.2, this dataclass owns every accumulator currently
    in the Stage B telemetry_state dict: iteration counter, dual metric traces (chi²/MSE),
    perf counters, variance-floor stats, sigma_floor tensor, and best snapshots.
    Stage B does not track lifecycle logs (U-matrix/A*) since crystal is frozen.

    Attributes:
        iteration_count: Mutable list wrapping iteration counter for closure capture (e.g., [0])
        loss_trace_sample: List of floats recording loss on sampled ROI subset per closure eval
        loss_trace_full: List of floats recording loss on full validation set
        best_loss_full: List of floats tracking best full-validation loss seen so far
        best_params_snapshot: List containing parameter snapshots at best loss (mutable container)
        chi_squared_trace_sample: List of floats recording chi² on sampled subset (PHYSICS-LOSS-001)
        chi_squared_trace_full: List of floats recording chi² on full validation set
        chi_squared_best: Tuple of (float, int) tracking best chi² and iteration
        masked_mse_trace_sample: List of floats recording masked MSE on sampled subset
        masked_mse_trace_full: List of floats recording masked MSE on full validation set
        masked_mse_best: Tuple of (float, int) tracking best masked MSE and iteration
        perf_closure_evals: Mutable list wrapping closure eval counter (e.g., [0])
        perf_validation_runs: Mutable list wrapping validation run counter (e.g., [0])
        perf_forward_times_ms: List of floats recording forward pass times in milliseconds
        variance_floor_clamped_pixels: Mutable list wrapping clamped pixel counter (e.g., [0])
        variance_floor_masked_pixels: Mutable list wrapping masked pixel counter (e.g., [0])
        sigma_floor_sq_tensor: Cached sigma_floor^2 tensor (PHYSICS-LOSS-002)

    Normative Dependencies:
    - Telemetry lists accumulate during LBFGS optimization per spec-db-workflow.md:48-84
    - Final telemetry dict assembled in stage_b.py::StageB.run and returned to engine
    - Variance floor stats per spec-db-core.md:57-68 (variance-weighted loss)
    - Dual metric tracking (chi² + masked MSE) per PHYSICS-LOSS-001/002

    IDL Contract Reference:
    - docs/spec-db-workflow.md:48-84 (Refinement Protocol Architecture)
    - ARCH-STAGE-CONTEXT-001: Telemetry dataclass refactoring

    Provenance:
    - ARCH-STAGE-CONTEXT-001 Phase B.3.2: Created to mirror Stage A telemetry structure
    """
    # Mutable counters (lists for closure capture)
    iteration_count: List[int] = field(default_factory=lambda: [0])
    perf_closure_evals: List[int] = field(default_factory=lambda: [0])
    perf_validation_runs: List[int] = field(default_factory=lambda: [0])
    variance_floor_clamped_pixels: List[int] = field(default_factory=lambda: [0])
    variance_floor_masked_pixels: List[int] = field(default_factory=lambda: [0])

    # Loss traces (floats)
    loss_trace_sample: List[float] = field(default_factory=list)
    loss_trace_full: List[float] = field(default_factory=list)
    best_loss_full: List[float] = field(default_factory=list)

    # Chi-squared traces (PHYSICS-LOSS-001)
    chi_squared_trace_sample: List[float] = field(default_factory=list)
    chi_squared_trace_full: List[float] = field(default_factory=list)
    chi_squared_best: List[float] = field(default_factory=lambda: [float('inf'), -1])

    # Masked MSE traces (PHYSICS-LOSS-001)
    masked_mse_trace_sample: List[float] = field(default_factory=list)
    masked_mse_trace_full: List[float] = field(default_factory=list)
    masked_mse_best: List[float] = field(default_factory=lambda: [float('inf'), -1])

    # Performance timing
    perf_forward_times_ms: List[float] = field(default_factory=list)

    # Best parameter snapshot (mutable container)
    best_params_snapshot: List[Any] = field(default_factory=list)

    # Variance floor tensor (cached, not a trace)
    sigma_floor_sq_tensor: Optional[Any] = None


@dataclass
class StageCTelemetryState:
    """
    Mutable telemetry accumulators for Stage C LBFGS refinement.

    Replaces the 'telemetry_state' dict passed through StageC._build_lbfgs_closure.
    Lists accumulate traces during optimization; counters track perf/validation stats.

    Per ARCH-STAGE-CONTEXT-001 Phase B.3.2, this dataclass owns every accumulator currently
    in the Stage C telemetry_state dict: iteration counter, dual metric traces (chi²/MSE),
    perf counters, variance-floor stats, sigma_floor tensor, best snapshots, and optional
    panel diagnostics for PERF-WARM-SIM-001.
    Stage C does not track lifecycle logs (U-matrix/A*) since crystal is frozen.

    Attributes:
        iteration_count: Mutable list wrapping iteration counter for closure capture (e.g., [0])
        loss_trace_sample: List of floats recording loss on sampled ROI subset per closure eval
        loss_trace_full: List of floats recording loss on full validation set
        best_loss_full: Tuple of (float, int) tracking best loss and iteration
        best_params_snapshot: Optional list containing parameter snapshots at best loss
        chi_squared_trace_sample: List of floats recording chi² on sampled subset (PHYSICS-LOSS-001)
        chi_squared_trace_full: List of floats recording chi² on full validation set
        chi_squared_best: Tuple of (float, int) tracking best chi² and iteration
        masked_mse_trace_sample: List of floats recording masked MSE on sampled subset
        masked_mse_trace_full: List of floats recording masked MSE on full validation set
        masked_mse_best: Tuple of (float, int) tracking best masked MSE and iteration
        perf_closure_evals: Mutable list wrapping closure eval counter (e.g., [0])
        perf_validation_runs: Mutable list wrapping validation run counter (e.g., [0])
        perf_forward_times_ms: List of floats recording forward pass times in milliseconds
        variance_floor_clamped_pixels: Mutable list wrapping clamped pixel counter (e.g., [0])
        variance_floor_masked_pixels: Mutable list wrapping masked pixel counter (e.g., [0])
        sigma_floor_sq_tensor: Cached sigma_floor^2 tensor (PHYSICS-LOSS-002)
        panel_loss_diag: Optional list for per-panel diagnostics (PERF-WARM-SIM-001), None if disabled

    Normative Dependencies:
    - Telemetry lists accumulate during LBFGS optimization per spec-db-workflow.md:48-84
    - Final telemetry dict assembled in stage_c.py::StageC.run and returned to engine
    - Variance floor stats per spec-db-core.md:57-68 (variance-weighted loss)
    - Dual metric tracking (chi² + masked MSE) per PHYSICS-LOSS-001/002
    - Panel diagnostics hook per PERF-WARM-SIM-001 (DBEX_STAGE_C_PANEL_DIAG_DIR)

    IDL Contract Reference:
    - docs/spec-db-workflow.md:48-84 (Refinement Protocol Architecture)
    - ARCH-STAGE-CONTEXT-001: Telemetry dataclass refactoring
    - REFINE-013: Best snapshot persistence

    Provenance:
    - ARCH-STAGE-CONTEXT-001 Phase B.3.2: Created to mirror Stage A telemetry structure
    """
    # Mutable counters (lists for closure capture)
    iteration_count: List[int] = field(default_factory=lambda: [0])
    perf_closure_evals: List[int] = field(default_factory=lambda: [0])
    perf_validation_runs: List[int] = field(default_factory=lambda: [0])
    variance_floor_clamped_pixels: List[int] = field(default_factory=lambda: [0])
    variance_floor_masked_pixels: List[int] = field(default_factory=lambda: [0])

    # Loss traces (floats)
    loss_trace_sample: List[float] = field(default_factory=list)
    loss_trace_full: List[float] = field(default_factory=list)
    best_loss_full: Tuple[float, int] = field(default_factory=lambda: (float('inf'), -1))

    # Chi-squared traces (PHYSICS-LOSS-001)
    chi_squared_trace_sample: List[float] = field(default_factory=list)
    chi_squared_trace_full: List[float] = field(default_factory=list)
    chi_squared_best: List[float] = field(default_factory=lambda: [float('inf'), -1])

    # Masked MSE traces (PHYSICS-LOSS-001)
    masked_mse_trace_sample: List[float] = field(default_factory=list)
    masked_mse_trace_full: List[float] = field(default_factory=list)
    masked_mse_best: List[float] = field(default_factory=lambda: [float('inf'), -1])

    # Performance timing
    perf_forward_times_ms: List[float] = field(default_factory=list)

    # Best parameter snapshot (mutable container)
    best_params_snapshot: Optional[List[Any]] = None

    # Variance floor tensor (cached, not a trace)
    sigma_floor_sq_tensor: Optional[Any] = None

    # Optional panel diagnostics (PERF-WARM-SIM-001 Phase D.4)
    panel_loss_diag: Optional[List[Any]] = None
