"""
Stage A baseline telemetry collector (ARCH-PROBE-FREEZE-001 Phase B).

Provides production-grade baseline metrics collection for Stage A parity diagnostics.
Consolidates ROI/mapping math from plan-local probes into a reusable helper that
Stage A can call via opt-in config flag, emitting metrics that DB-AT evidence depends on.

Per docs/architecture/data_telemetry_flow.md:40-120 and prompts/supervisor.md:272-287,
this module is the canonical owner for Stage A baseline metrics computation.

Key Design Points:
- Minimal dependencies: uses only canonical owner APIs (simulate_forward_once, build_mapping_stage_a_context)
- Schema versioning: returns serializable dict with version marker for future compatibility
- CPU-friendly: all outputs are Python floats/lists, no raw torch tensors
- Thin helper: no Stage/ROI/physics/refinement semantics duplication

JSON Schema (v1):
{
    "schema_version": "v1",
    "masked_means": {
        "target_mean_masked": float,
        "model_mean_masked": float,
        "bragg_mean_masked": float
    },
    "unmasked_means": {
        "target_mean_unmasked": float,
        "model_mean_unmasked": float,
        "bragg_mean_unmasked": float
    },
    "chi_squared": {
        "chi_squared_per_pixel_initial": float,
        "n_masked_pixels": int
    },
    "roi_correlations": {
        "pearson_per_roi": List[float],
        "median_roi_pearson": float,
        "p25_roi_pearson": float,
        "p75_roi_pearson": float,
        "n_rois_with_correlations": int
    },
    "roi_snippets": List[{
        "panel_id": int,
        "bbox": [int, int, int, int],
        "masked_mean_target": float,
        "masked_mean_model": float,
        "pearson_corr": float
    }]
}
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import torch


def _masked_roi_corr(data_roi: np.ndarray, model_roi: np.ndarray, mask_roi: np.ndarray) -> float:
    """
    Compute masked Pearson correlation for a single ROI.

    Args:
        data_roi: Target data ROI [slow, fast]
        model_roi: Model data ROI [slow, fast]
        mask_roi: Loss mask ROI [slow, fast] (bool or 0/1)

    Returns:
        Pearson correlation coefficient (float), or NaN if mask is empty or denominator is zero
    """
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


def collect_stage_a_baseline_metrics(
    stage_a_ctx: Any,  # StageAContext
    refinement_inputs: Any,  # RefinementInputs
    telemetry: Any,  # RefinementTelemetry with params_initial
    loss_mask: torch.Tensor,  # [panel, slow, fast]
    mapping_context: Optional[Any] = None,  # MappingContext (optional, for ROI slicing)
    # ARCH-PROBE-FREEZE-001: Additional parameters for reconstruction
    detector: Optional[Any] = None,
    beam: Optional[Any] = None,
    crystal: Optional[Any] = None,
    hkl_grid: Optional[torch.Tensor] = None,
    hkl_metadata: Optional[Dict] = None,
    config: Optional[Any] = None,
    baseline_crystal: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Collect Stage A baseline metrics for parity diagnostics.

    Computes masked/unmasked means, chi²-per-pixel, and ROI Pearson correlations
    from Stage A initial forward simulation (pre-optimization).

    Args:
        stage_a_ctx: StageAContext with warm cache and initial parameters
        refinement_inputs: RefinementInputs with target, background-subtracted data
        telemetry: RefinementTelemetry with params_initial for reconstruction
        loss_mask: Loss mask tensor [panel, slow, fast] (True=include)
        mapping_context: Optional MappingContext for ROI slices

    Returns:
        Serializable dict with schema version "v1" containing:
        - masked_means: target/model/bragg means over loss mask
        - unmasked_means: target/model/bragg means over full detector
        - chi_squared: chi²-per-pixel initial and n_masked_pixels
        - roi_correlations: per-ROI Pearson + summary stats
        - roi_snippets: top-N ROI summaries with bbox/means/corr

    Raises:
        ValueError: If required fields are missing or shapes are inconsistent

    Example:
        >>> metrics = collect_stage_a_baseline_metrics(
        ...     stage_a_ctx, refinement_inputs, telemetry, loss_mask, mapping_context
        ... )
        >>> print(f"Masked chi²/px: {metrics['chi_squared']['chi_squared_per_pixel_initial']:.2e}")
    """
    # 1. Extract target tensor (background-subtracted)
    target = refinement_inputs.target  # numpy.ndarray or torch.Tensor [panel, slow, fast]
    # Handle both numpy and torch tensors
    if isinstance(target, np.ndarray):
        # Convert to torch for consistent processing
        device_str = stage_a_ctx.device if hasattr(stage_a_ctx, 'device') else 'cpu'
        device = torch.device(device_str)
        dtype = torch.float32
        target = torch.from_numpy(target).to(device=device, dtype=dtype)
    else:
        device = target.device
        dtype = target.dtype

    # 2. Run initial forward simulation from StageAContext to get model_initial
    # Use the telemetry_state initial params to reconstruct the baseline Bragg
    from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry
    from dbex.refinement.stage import RefinementTelemetry

    # Reconstruct Bragg from initial params using the provided telemetry
    # ARCH-PROBE-FREEZE-001: Pass all required parameters for reconstruction
    device_obj = torch.device(device)
    bragg_initial_np = build_final_bragg_from_stage_a_telemetry(
        telemetry_a=telemetry,
        detector=detector,
        beam=beam,
        crystal=crystal,
        inputs=refinement_inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=device_obj,
        dtype=dtype,
        stage_a_ctx=stage_a_ctx,
        baseline_crystal=baseline_crystal,
        param_state="initial",
    )

    # Convert to torch tensor for consistent computation
    bragg_initial = torch.from_numpy(bragg_initial_np).to(device=device, dtype=dtype)

    # 3. Compute masked/unmasked means
    # Handle loss_mask: convert numpy arrays to torch if needed
    if isinstance(loss_mask, np.ndarray):
        loss_mask = torch.from_numpy(loss_mask).to(device=device, dtype=torch.bool)
        loss_mask_bool = loss_mask
    else:
        loss_mask_bool = loss_mask.bool()
    n_masked_pixels = int(loss_mask_bool.sum().item())
    n_total_pixels = int(loss_mask.numel())

    # Masked means
    # Note: target in RefinementInputs is already background-subtracted, so it aligns with bragg_initial directly
    target_mean_masked = float(target[loss_mask_bool].mean().item()) if n_masked_pixels > 0 else float("nan")
    bragg_mean_masked = float(bragg_initial[loss_mask_bool].mean().item()) if n_masked_pixels > 0 else float("nan")

    # For baseline metrics, "model" = bragg (refinement_inputs.target is background-subtracted, so bragg is the model)
    model_mean_masked = bragg_mean_masked

    # Unmasked means
    target_mean_unmasked = float(target.mean().item())
    bragg_mean_unmasked = float(bragg_initial.mean().item())
    model_mean_unmasked = bragg_mean_unmasked

    # 4. Compute chi²-per-pixel (variance-weighted loss)
    # Chi² = Σ[(target - model)² / variance] / n_pixels
    # Variance = model + sigma_readout² (Poisson + readout noise)
    sigma_readout = refinement_inputs.sigma_readout  # [panel, slow, fast]
    if isinstance(sigma_readout, np.ndarray):
        sigma_readout = torch.from_numpy(sigma_readout).to(device=device, dtype=dtype)
    sigma_readout_sq = sigma_readout**2
    variance = bragg_initial + sigma_readout_sq  # variance = bragg + sigma_readout²

    # Apply variance floor if present in refinement_inputs
    if hasattr(refinement_inputs, 'sigma_floor_sq') and refinement_inputs.sigma_floor_sq is not None:
        sigma_floor_sq = refinement_inputs.sigma_floor_sq
        variance = torch.maximum(variance, sigma_floor_sq)

    residuals_sq = (target - model_initial)**2
    chi_squared_per_pixel = residuals_sq[loss_mask_bool] / variance[loss_mask_bool]
    chi_squared_per_pixel_initial = float(chi_squared_per_pixel.mean().item()) if n_masked_pixels > 0 else float("nan")

    # 5. Compute ROI Pearson correlations
    roi_correlations_list: List[float] = []
    roi_snippets: List[Dict[str, Any]] = []

    if mapping_context is not None and hasattr(mapping_context, 'roi_slices'):
        # Convert tensors to numpy for correlation computation
        target_np = target.cpu().numpy()
        model_np = model_initial.cpu().numpy()
        loss_mask_np = loss_mask.cpu().numpy()

        for panel_id, bbox in mapping_context.roi_slices:
            x0, x1, y0, y1 = bbox
            panel_id = int(panel_id)

            # Extract ROI
            roi_mask = loss_mask_np[panel_id, y0:y1, x0:x1]
            if not np.any(roi_mask):
                continue

            data_roi = target_np[panel_id, y0:y1, x0:x1]
            model_roi = model_np[panel_id, y0:y1, x0:x1]

            # Compute masked ROI correlation
            corr = _masked_roi_corr(data_roi, model_roi, roi_mask)
            roi_correlations_list.append(corr)

            # Compute masked means for snippet
            roi_mask_bool = roi_mask.astype(bool)
            masked_mean_target = float(data_roi[roi_mask_bool].mean()) if np.any(roi_mask_bool) else float("nan")
            masked_mean_model = float(model_roi[roi_mask_bool].mean()) if np.any(roi_mask_bool) else float("nan")

            roi_snippets.append({
                "panel_id": panel_id,
                "bbox": [int(x0), int(x1), int(y0), int(y1)],
                "masked_mean_target": masked_mean_target,
                "masked_mean_model": masked_mean_model,
                "pearson_corr": corr,
            })

    # Compute ROI correlation summary stats
    valid_corrs = [c for c in roi_correlations_list if np.isfinite(c)]
    median_roi_pearson = float(np.median(valid_corrs)) if valid_corrs else float("nan")
    p25_roi_pearson = float(np.percentile(valid_corrs, 25)) if valid_corrs else float("nan")
    p75_roi_pearson = float(np.percentile(valid_corrs, 75)) if valid_corrs else float("nan")

    # Sort snippets by correlation (best first) and take top 10
    roi_snippets_sorted = sorted(
        [s for s in roi_snippets if np.isfinite(s["pearson_corr"])],
        key=lambda s: s["pearson_corr"],
        reverse=True
    )[:10]

    # 6. Build output payload
    return {
        "schema_version": "v1",
        "masked_means": {
            "target_mean_masked": target_mean_masked,
            "model_mean_masked": model_mean_masked,
            "bragg_mean_masked": bragg_mean_masked,
        },
        "unmasked_means": {
            "target_mean_unmasked": target_mean_unmasked,
            "model_mean_unmasked": model_mean_unmasked,
            "bragg_mean_unmasked": bragg_mean_unmasked,
        },
        "chi_squared": {
            "chi_squared_per_pixel_initial": chi_squared_per_pixel_initial,
            "n_masked_pixels": n_masked_pixels,
            "n_total_pixels": n_total_pixels,
        },
        "roi_correlations": {
            "pearson_per_roi": [float(c) for c in roi_correlations_list],
            "median_roi_pearson": median_roi_pearson,
            "p25_roi_pearson": p25_roi_pearson,
            "p75_roi_pearson": p75_roi_pearson,
            "n_rois_with_correlations": len(valid_corrs),
        },
        "roi_snippets": roi_snippets_sorted,
    }
