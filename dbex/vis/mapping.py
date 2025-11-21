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
    """Container for mapping-based Stage A inputs and outputs."""

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
    repo_root = mtz_path.resolve().parent
    fixtures_root = repo_root / "tests" / "fixtures" / "golden_data" / "simple_cubic"
    config_json = fixtures_root / "config_torch.json"
    refined_mtz = fixtures_root / "refined_structure_factors.mtz"

    hkl_indices = dataload.F.indices()
    hkl_amplitudes = dataload.F.data()
    hkl_source = None
    hkl_path = None

    calibration = None
    if config_json.exists():
        try:
            calibration = load_calibration_metadata(config_json)
        except Exception:
            calibration = None

    if refined_mtz.exists():
        try:
            hkl_indices, hkl_amplitudes = load_refined_mtz(refined_mtz, column="F")
            hkl_source = "refined"
            hkl_path = str(refined_mtz.resolve())
        except Exception:
            hkl_source = "raw"
            hkl_path = str(mtz_path.resolve())
    else:
        hkl_source = "raw"
        hkl_path = str(mtz_path.resolve())

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


__all__ = [
    "MappingStageAContext",
    "MappingRefinementConfig",
    "MappingRefinementResult",
    "build_mapping_stage_a_context",
    "refine_on_mapping_model",
]
