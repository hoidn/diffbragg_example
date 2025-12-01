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
from typing import Any, Dict, Optional

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
        extras: Dict[str, Any] for future extensions (job metadata, provenance, etc.)

    Normative Dependencies (Transitive):
    - refinement_inputs.target: Prepared per spec-db-core.md:20 ([panel, slow, fast])
    - refinement_inputs.loss_mask: (background >= 0) ∧ trusted_mask per spec-db-core.md:55
    - detector: dxtbx Detector with square pixels per config_crosswalk.md:30
    - beam: dxtbx Beam with wavelength and polarization per config_crosswalk.md:65-70
    - crystal: dxtbx Crystal with unit cell and orientation per config_crosswalk.md:75-80
    - hkl_grid: Structure factors per spec-db-core.md:85-90 (refined MTZ preferred)
    - hkl_metadata['has_halo']: Stage B/C require halo-padded grid per spec-db-workflow.md:53-54

    IDL Contract Reference:
    - docs/architecture.md (modular structure)
    - docs/spec-db-workflow.md:48-84 (Refinement Protocol Architecture)
    """
    refinement_inputs: Any  # RefinementInputs from dbex.nanobrag_bridge
    detector: Any  # dxtbx Detector object
    beam: Any  # dxtbx Beam object
    crystal: Any  # dxtbx Crystal object
    hkl_grid: torch.Tensor  # [h, k, l] complex structure factor grid
    hkl_metadata: Dict[str, Any]  # nabc_grid, default_F, has_halo, etc.
    baseline_crystal: Optional[Any] = None  # baseline dxtbx Crystal (for misset extraction)
    baseline_detector: Optional[Any] = None  # baseline dxtbx Detector (for Stage C offsets)
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
    extras: Optional[Dict[str, Any]] = None,
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
        extras: Optional dict for future extensions (job metadata, provenance, etc.)

    Returns:
        RefinementContext instance with validated inputs

    Raises:
        ValueError: If hkl_grid is not a torch.Tensor or hkl_metadata is missing required keys
        TypeError: If detector/beam/crystal are not dxtbx objects (future validation)

    Normative Requirements:
    - hkl_grid must be a torch.Tensor per spec-db-core.md:85-90
    - hkl_metadata must contain 'nabc_grid' and 'has_halo' keys per spec-db-workflow.md:53-54
    - Device/dtype neutrality: this builder does NOT enforce specific device/dtype;
      stages are responsible for tensor device/dtype management per pytorch_runtime_checklist.md

    Provenance:
    - ARCH-REFINE-001 Phase B.1: Replace ad-hoc dict plumbing with typed context
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
