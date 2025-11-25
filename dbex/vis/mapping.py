"""Mapping-aligned helpers for Stage A visualization.

This module provides a thin wrapper around the DB-AT-024 mapping forward
model so tooling under TOOLING-VIS-001 can generate Stage A visuals where
both "before" and "after" share the same forward simulator and variance
semantics.

The helpers are intentionally conservative:
- ``build_mapping_stage_a_context`` reuses the canonical
  ``simulate_forward_once`` helper with refined structure factors and
  calibration metadata when available, mirroring DB-AT-024.
- ``refine_on_mapping_model`` runs a vis-only, scale-only optimization on
  top of the zero-iteration Bragg stack using the same variance-weighted
  chi-squared definition as ``simulate_forward_once`` diagnostics.

These utilities are designed for plan-local tooling and are not part of the
canonical refinement engine. They must not mutate production configs or
change Stage A behavior inside ``run_nanobrag_refinement``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    RefinementInputs,
    load_calibration_metadata,
    load_refined_mtz,
    prepare_refinement_inputs,
    simulate_forward_once,
)


@dataclass
class MappingStageAContext:
    """Container for mapping-based Stage A inputs and outputs.

    This context is the canonical "truth" configuration for mapping-aligned
    Stage A helpers:
    - ``bragg_zero_iter`` and ``diagnostics['chi_squared']`` come directly
      from :func:`simulate_forward_once` using the DB-AT-024 mapping path
      (refined MTZ + calibration when available).
    - Geometry and variance semantics here define the zero-parameter
      Stage A baseline that plan-local tooling (e.g. Adam debug helpers)
      must reproduce at their own zero-point before enabling geometry DoFs.
    """

    inputs: RefinementInputs
    bragg_zero_iter: np.ndarray
    sigma_floor_value: float
    diagnostics: Dict[str, object]
    # Optional fields used by plan-local refinement helpers
    hkl_indices: Optional[np.ndarray] = None
    hkl_amplitudes: Optional[np.ndarray] = None
    calibration: Optional[dict] = None
    spot_scale_override: Optional[float] = None
    device: Optional[str] = None


@dataclass
class MappingRefinementConfig:
    """Configuration for mapping-based vis-only refinement."""

    n_steps: int = 100
    learning_rate: float = 1e-3
    device: str = "cpu"
    dtype: str = "float32"
    max_log_scale: float = 10.0
    min_log_scale: float = -10.0


@dataclass
class MappingRefinementResult:
    """Result for mapping-based refinement."""

    bragg_after: np.ndarray
    loss_trace: List[float]
    final_scale: float


def _select_sigma_readout(dataload: DataLoad, default_sigma: float = 3.0) -> np.ndarray:
    """Choose a sigma_readout tensor aligned to DataLoad.data."""
    sigma_map = getattr(dataload, "sigma_readout_map", None)
    sigma_source = getattr(dataload, "sigma_readout_map_source", None)
    if sigma_map is not None and sigma_source == "external_lookup":
        return np.asarray(sigma_map, dtype=np.float32)
    return np.full_like(dataload.data, float(default_sigma), dtype=np.float32)


def build_mapping_stage_a_context(
    dataload: DataLoad,
    *,
    default_sigma_readout: float = 3.0,
    device: str = "cpu",
) -> MappingStageAContext:
    """Build a mapping-based Stage A context for visualization.

    This helper mirrors the DB-AT-024 mapping pipeline:
    - Uses :class:`DataLoad` to prepare canonical refGeom assets.
    - Builds :class:`RefinementInputs` via :func:`prepare_refinement_inputs`,
      preferring calibrated sigma tiles when available and falling back to a
      uniform sigma value otherwise.
    - Runs :func:`simulate_forward_once` with refined structure factors and
      calibration metadata when those assets exist; otherwise falls back to
      the raw scaled MTZ.
    - Returns the zero-iteration Bragg stack plus the ``sigma_floor_value``
      used inside the diagnostics block.

    Data dependencies:
        - HKL provenance defaults to ``dataload.args.mtzFile`` but MAY be
          overridden via ``dataload.args.hkl_source_path`` (e.g.,
          ``DBEX_SMOKE_HKL_PATH``). Callers SHALL pass the correct HKL asset for
          their dataset rather than relying on a global fixture.
        - Calibration metadata MAY be provided via
          ``dataload.args.calibration_config_path``; when absent the helper
          SHALL leave ``calibration=None`` instead of falling back to the golden
          config.
        - Sigma maps come from ``dataload.sigma_readout_map`` (map tier) or the
          ``default_sigma_readout`` fallback. Provenance is recorded inside
          ``RefinementInputs``.
        - Diagnostics MUST record the chosen HKL/calibration paths so telemetry
          consumers can audit the mapping inputs.

    Args:
        dataload: Initialized :class:`DataLoad` instance for the target assets.
        default_sigma_readout: Fallback sigma value (in ADU) when no calibrated
            sigma map is available.
        device: Torch device string forwarded to :func:`simulate_forward_once`.

    Returns:
        MappingStageAContext with prepared inputs, zero-iteration Bragg stack,
        and variance-floor diagnostics.
    """
    sigma_readout = _select_sigma_readout(dataload, default_sigma=default_sigma_readout)

    inputs = prepare_refinement_inputs(
        data=dataload.data,
        background_image=dataload.background_image,
        trusted_mask=dataload.trusted_mask,
        bbox=dataload.bbox,
        pids=dataload.pids,
        detector=dataload.detector,
        adu_per_photon=None,
        sigma_readout=sigma_readout,
    )

    mtz_path = Path(getattr(dataload.args, "mtzFile"))

    # Respect hkl_source_path when provided; otherwise use mtzFile
    hkl_source_path_override = getattr(dataload.args, "hkl_source_path", None)
    if hkl_source_path_override is not None:
        hkl_source_path_to_check = Path(hkl_source_path_override)
    else:
        hkl_source_path_to_check = mtz_path

    # Use the MTZ path from DataLoad for raw; determine if we should load refined
    hkl_indices = dataload.F.indices()
    hkl_amplitudes = dataload.F.data()

    # Check if the HKL source path is a refined structure factors file
    if "refined_structure_factors" in hkl_source_path_to_check.name and hkl_source_path_to_check.exists():
        try:
            hkl_indices, hkl_amplitudes = load_refined_mtz(hkl_source_path_to_check, column="F")
            hkl_source = "refined"
            hkl_path = str(hkl_source_path_to_check.resolve())
        except Exception:
            # Fallback to dataload.F if refined loading fails
            hkl_source = "raw"
            hkl_path = str(mtz_path.resolve())
    else:
        hkl_source = "raw"
        hkl_path = str(hkl_source_path_to_check.resolve())

    # Only load calibration when explicitly provided via calibration_config_path
    calibration = None
    calibration_config_path = getattr(dataload.args, "calibration_config_path", None)
    if calibration_config_path is not None:
        calibration_config_path = Path(calibration_config_path)
        if calibration_config_path.exists():
            try:
                calibration = load_calibration_metadata(calibration_config_path)
            except Exception:
                calibration = None

    bragg_zero_iter, diagnostics = simulate_forward_once(
        inputs=inputs,
        detector=dataload.detector,
        beam=dataload.beam,
        crystal=dataload.crystal,
        experiment=dataload.Expt,
        hkl_indices=hkl_indices,
        hkl_amplitudes=hkl_amplitudes,
        calibration=calibration,
        hkl_source=hkl_source,
        hkl_path=hkl_path,
        device=device,
    )

    if diagnostics is None:
        diagnostics = {}

    # Record the calibration path actually used in diagnostics
    diagnostics["calibration_path"] = (
        str(calibration_config_path.resolve())
        if calibration_config_path is not None and calibration_config_path.exists()
        else None
    )

    sigma_floor_value = float(diagnostics.get("sigma_floor_value", 1.0))

    # Warm-start global_scale_hint from masked means in ADU mode.
    num = float(inputs.target[inputs.loss_mask].mean())
    den = float(bragg_zero_iter[inputs.loss_mask].mean())
    if den > 1e-12:
        inputs.global_scale_hint = num / den

    # Extract spot_scale_override used inside simulate_forward_once (if available)
    spot_scale_used = diagnostics.get("spot_scale_override")
    try:
        spot_scale_used = float(spot_scale_used) if spot_scale_used is not None else None
    except (TypeError, ValueError):
        spot_scale_used = None

    return MappingStageAContext(
        inputs=inputs,
        bragg_zero_iter=bragg_zero_iter,
        sigma_floor_value=sigma_floor_value,
        diagnostics=diagnostics,
        hkl_indices=hkl_indices,
        hkl_amplitudes=hkl_amplitudes,
        calibration=calibration,
        spot_scale_override=spot_scale_used,
        device=str(device) if device is not None else None,
    )


def refine_on_mapping_model(
    inputs: RefinementInputs,
    bragg_zero_iter: np.ndarray,
    sigma_floor_value: float,
    config: Optional[MappingRefinementConfig] = None,
) -> MappingRefinementResult:
    """Run a vis-only, scale-only refinement on the mapping model.

    The mapping Bragg stack is treated as the fixed base model. A single
    global ``log_scale`` parameter is optimized using a variance-weighted
    chi-squared loss:

        V = I_model.detach() + sigma_readout**2
        chi2 = sum((I_model - I_obs)**2 / max(V, sigma_floor**2))

    Args:
        inputs: RefinementInputs produced by ``prepare_refinement_inputs``.
        bragg_zero_iter: Zero-iteration Bragg stack shaped [panel, slow, fast].
        sigma_floor_value: Variance floor (sigma_floor) in target units.
        config: Optional MappingRefinementConfig controlling optimizer settings.

    Returns:
        MappingRefinementResult with refined Bragg stack and loss trace.
    """
    import torch

    if config is None:
        config = MappingRefinementConfig()

    target = torch.tensor(
        np.asarray(inputs.target), device=config.device, dtype=getattr(torch, config.dtype)
    )
    sigma = torch.tensor(
        np.asarray(inputs.sigma_readout),
        device=config.device,
        dtype=getattr(torch, config.dtype),
    )
    mask = torch.tensor(
        np.asarray(inputs.loss_mask), device=config.device, dtype=torch.bool
    )
    bragg_base = torch.tensor(
        np.asarray(bragg_zero_iter),
        device=config.device,
        dtype=getattr(torch, config.dtype),
    )

    if target.shape != bragg_base.shape:
        raise ValueError(
            f"Target and bragg_zero_iter must share shape; "
            f"got target={target.shape}, bragg_zero_iter={bragg_base.shape}"
        )
    if sigma.shape != target.shape:
        raise ValueError(
            f"sigma_readout shape {sigma.shape} does not match target shape {target.shape}"
        )
    if mask.shape != target.shape:
        raise ValueError(
            f"loss_mask shape {mask.shape} does not match target shape {target.shape}"
        )

    if sigma_floor_value <= 0.0:
        raise ValueError(
            f"sigma_floor_value must be > 0 (got {sigma_floor_value})."
        )

    if inputs.global_scale_hint is not None and inputs.global_scale_hint > 0:
        initial_log_scale = float(np.log(inputs.global_scale_hint))
    else:
        initial_log_scale = 0.0

    log_scale = torch.tensor(
        initial_log_scale,
        device=config.device,
        dtype=getattr(torch, config.dtype),
        requires_grad=True,
    )

    optimizer = torch.optim.Adam([log_scale], lr=config.learning_rate)
    sigma_floor_sq = torch.tensor(
        float(sigma_floor_value ** 2),
        device=config.device,
        dtype=getattr(torch, config.dtype),
    )

    loss_trace: List[float] = []

    for _ in range(int(config.n_steps)):
        optimizer.zero_grad()

        log_scale_clamped = torch.clamp(
            log_scale,
            min=float(config.min_log_scale),
            max=float(config.max_log_scale),
        )
        scale = torch.exp(log_scale_clamped)
        prediction = bragg_base * scale

        variance_raw = prediction.detach() + sigma ** 2
        variance = torch.clamp(variance_raw, min=sigma_floor_sq)

        diff_sq = (prediction - target) ** 2
        weighted = diff_sq / variance
        masked_weighted = torch.where(mask, weighted, torch.zeros_like(weighted))
        loss = masked_weighted.sum()

        loss.backward()
        optimizer.step()

        loss_trace.append(float(loss.item()))

    final_log_scale = float(log_scale.detach().cpu().item())
    final_scale = float(np.exp(final_log_scale))
    with torch.no_grad():
        final_prediction = (bragg_base * torch.tensor(final_scale, device=config.device)).cpu()

    bragg_after = final_prediction.numpy().astype(np.float32, copy=False)
    return MappingRefinementResult(
        bragg_after=bragg_after,
        loss_trace=loss_trace,
        final_scale=final_scale,
    )


def emit_mapping_context_diagnostics(
    mapping_context: MappingStageAContext,
    dataload: DataLoad,
    output_path: Path,
    *,
    bragg_model: Optional[np.ndarray] = None,
    stage_name: str = "mapping",
) -> None:
    """Emit mapping context diagnostics to JSON before assertions.

    This helper captures dataset paths, sigma provenance, HKL source/path,
    target/loss_mask stats, ROI CC/scale ratios, and device information
    to a JSON artifact. It is designed to be called BEFORE gating assertions
    so that diagnostic context is preserved even when tests fail.

    Args:
        mapping_context: The MappingStageAContext instance to diagnose.
        dataload: DataLoad instance containing dataset metadata.
        output_path: Path to the output JSON file.
        bragg_model: Optional Bragg model stack (same shape as target) for
            computing ROI correlations and scale ratios. If None, diagnostics
            will skip correlation and scale metrics.
        stage_name: Human-readable name for this diagnostic stage (e.g.,
            "mapping", "probe", "fixture"). Included in the JSON output.

    Returns:
        None. Writes a JSON file to ``output_path`` with diagnostic fields:
        - timestamp: ISO8601 UTC timestamp
        - stage_name: The stage_name argument
        - dataset_paths: dict with expt, refl, mask, mtz paths
        - sigma_provenance: string describing sigma_readout source
        - hkl_source: string (e.g., "refined", "raw")
        - hkl_path: absolute path to the HKL file
        - calibration_path: path to calibration config file from diagnostics (or null)
        - geometry_path: resolved canonical geometry path from refgeom_dataload (or null)
        - rotation_delta_deg: rotation angle between loaded and canonical U-matrix (or null)
        - origin_delta_mm: detector origin drift in mm (or null)
        - geometry_overridden: boolean indicating if geometry was overridden (or null)
        - device: device string from mapping_context
        - target_stats: dict with mean, std, min, max over loss_mask
        - target_mean_masked: mean of target over loss_mask
        - target_mean_unmasked: mean of target over all pixels
        - bragg_mean_masked: mean of bragg_model over loss_mask (if bragg_model provided)
        - bragg_mean_unmasked: mean of bragg_model over all pixels (if bragg_model provided)
        - loss_mask_coverage: fraction of pixels included in loss_mask
        - n_rois: number of ROIs in panel_slices
        - roi_cc_median: median Pearson CC over ROIs (if bragg_model provided)
        - scale_ratio_masked: mean(bragg_model[mask]) / mean(target[mask]) (if bragg_model)
        - scale_ratio_unmasked: mean(bragg_model) / mean(target) (if bragg_model)
        - global_scale_hint: global_scale_hint from mapping_context.inputs (or null)
        - sigma_floor_value: sigma_floor used in mapping context
        - spot_scale_override: spot_scale_override from mapping_context (or null)
    """
    import json
    from datetime import datetime, timezone
    from statistics import median

    # Ensure parent directory exists
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Extract dataset paths from dataload
    args_ns = getattr(dataload, "args", None)
    dataset_paths = {
        "expt": str(getattr(args_ns, "exptName", None)),
        "refl": str(getattr(args_ns, "reflName", None)),
        "mask": str(getattr(args_ns, "maskFile", None)),
        "mtz": str(getattr(args_ns, "mtzFile", None)),
    }

    # Determine sigma provenance
    sigma_map_source = getattr(dataload, "sigma_readout_map_source", None)
    if sigma_map_source == "external_lookup":
        sigma_provenance = "external_lookup (metadata tiles)"
    else:
        sigma_provenance = "cli_override (default scalar)"

    # HKL source/path from diagnostics
    hkl_source = mapping_context.diagnostics.get("hkl_source", "unknown")
    hkl_path = mapping_context.diagnostics.get("hkl_path", "unknown")

    # Calibration path from diagnostics (TOOLING-VIS-001)
    calibration_path = mapping_context.diagnostics.get("calibration_path", None)

    # Device
    device = mapping_context.device or "unknown"

    # Target and loss_mask stats
    inputs = mapping_context.inputs
    target = np.asarray(inputs.target, dtype=np.float64)
    loss_mask = np.asarray(inputs.loss_mask, dtype=bool)
    masked_target = target[loss_mask]

    target_stats = {
        "mean": float(np.mean(masked_target)),
        "std": float(np.std(masked_target)),
        "min": float(np.min(masked_target)),
        "max": float(np.max(masked_target)),
    }

    # Compute masked and unmasked target means
    target_mean_masked = float(np.mean(masked_target))
    target_mean_unmasked = float(np.mean(target))

    total_pixels = int(np.prod(target.shape))
    masked_pixels = int(np.count_nonzero(loss_mask))
    loss_mask_coverage = float(masked_pixels / total_pixels) if total_pixels > 0 else 0.0

    n_rois = len(inputs.panel_slices)

    # ROI correlations and scale ratio (optional, requires bragg_model)
    roi_cc_median = None
    scale_ratio_masked = None
    scale_ratio_unmasked = None
    bragg_mean_masked = None
    bragg_mean_unmasked = None
    if bragg_model is not None:
        bragg_model_arr = np.asarray(bragg_model, dtype=np.float64)
        if bragg_model_arr.shape != target.shape:
            raise ValueError(
                f"bragg_model shape {bragg_model_arr.shape} does not match "
                f"target shape {target.shape}"
            )

        # Compute per-ROI correlations
        def _pearson_cc(data_roi, model_roi, mask_roi):
            mask_flat = np.asarray(mask_roi, dtype=bool)
            if not np.any(mask_flat):
                return float("nan")
            data = np.asarray(data_roi, dtype=np.float64)[mask_flat]
            model = np.asarray(model_roi, dtype=np.float64)[mask_flat]
            data_centered = data - data.mean()
            model_centered = model - model.mean()
            denom = np.linalg.norm(data_centered) * np.linalg.norm(model_centered)
            if denom <= 0:
                return float("nan")
            return float(np.dot(data_centered, model_centered) / denom)

        corrs = []
        for pid, bbox in inputs.panel_slices:
            x0, x1, y0, y1 = bbox
            roi_mask = loss_mask[int(pid), y0:y1, x0:x1]
            if not np.any(roi_mask):
                continue
            data_roi = target[int(pid), y0:y1, x0:x1]
            model_roi = bragg_model_arr[int(pid), y0:y1, x0:x1]
            corrs.append(_pearson_cc(data_roi, model_roi, roi_mask))

        valid_corrs = [c for c in corrs if np.isfinite(c)]
        roi_cc_median = float(median(valid_corrs)) if valid_corrs else float("nan")

        # Compute masked and unmasked Bragg means and scale ratios
        bragg_mean_masked = float(np.mean(bragg_model_arr[loss_mask]))
        bragg_mean_unmasked = float(np.mean(bragg_model_arr))

        scale_ratio_masked = bragg_mean_masked / target_mean_masked if target_mean_masked > 0 else float("inf")
        scale_ratio_unmasked = bragg_mean_unmasked / target_mean_unmasked if target_mean_unmasked > 0 else float("inf")

    # Sigma floor and spot scale
    sigma_floor_value = float(mapping_context.sigma_floor_value)
    spot_scale_override = mapping_context.spot_scale_override
    if spot_scale_override is not None:
        spot_scale_override = float(spot_scale_override)

    # Geometry metadata from dataload fixture (TOOLING-VIS-001)
    geometry_metadata = getattr(dataload, "geometry_metadata", None)
    if geometry_metadata:
        geometry_path = geometry_metadata.get("geometry_path")
        rotation_delta_deg = geometry_metadata.get("rotation_delta_deg")
        origin_delta_mm = geometry_metadata.get("origin_delta_mm")
        geometry_overridden = geometry_metadata.get("geometry_overridden")
    else:
        geometry_path = None
        rotation_delta_deg = None
        origin_delta_mm = None
        geometry_overridden = None

    # Extract global_scale_hint from mapping context inputs
    global_scale_hint = inputs.global_scale_hint
    if global_scale_hint is not None:
        global_scale_hint = float(global_scale_hint)

    # Build diagnostics dict
    diagnostics_dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage_name": stage_name,
        "dataset_paths": dataset_paths,
        "sigma_provenance": sigma_provenance,
        "hkl_source": hkl_source,
        "hkl_path": hkl_path,
        "calibration_path": calibration_path,
        "geometry_path": geometry_path,
        "rotation_delta_deg": rotation_delta_deg,
        "origin_delta_mm": origin_delta_mm,
        "geometry_overridden": geometry_overridden,
        "device": device,
        "target_stats": target_stats,
        "target_mean_masked": target_mean_masked,
        "target_mean_unmasked": target_mean_unmasked,
        "bragg_mean_masked": bragg_mean_masked,
        "bragg_mean_unmasked": bragg_mean_unmasked,
        "loss_mask_coverage": loss_mask_coverage,
        "n_rois": n_rois,
        "roi_cc_median": roi_cc_median,
        "scale_ratio_masked": scale_ratio_masked,
        "scale_ratio_unmasked": scale_ratio_unmasked,
        "global_scale_hint": global_scale_hint,
        "sigma_floor_value": sigma_floor_value,
        "spot_scale_override": spot_scale_override,
    }

    # Write JSON
    with output_path.open("w") as f:
        json.dump(diagnostics_dict, f, indent=2)


__all__ = [
    "MappingStageAContext",
    "MappingRefinementConfig",
    "MappingRefinementResult",
    "build_mapping_stage_a_context",
    "refine_on_mapping_model",
    "emit_mapping_context_diagnostics",
]
