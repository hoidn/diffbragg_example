import json
import os
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest
import torch

from dbex.nanobrag_bridge import (
    build_structure_factor_grid,
)
from dbex.nanobrag_refinement import (
    RefinementConfig,
    _build_final_bragg_from_stage_a_telemetry,
    run_nanobrag_refinement,
)
from dbex.vis.mapping import (
    build_mapping_stage_a_context,
    emit_mapping_context_diagnostics,
)
from tests.dbex.test_torch_refine_smoke import create_perturbed_geometry

pytest_plugins = ["tests.dbex.test_torch_refine_smoke"]


def _artifact_dir(env_var: str) -> Path:
    path = os.environ.get(env_var)
    if not path:
        pytest.skip(f"{env_var} not set; export per input.md to capture DB-AT metrics")
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    return out


def _masked_roi_corr(data_roi: np.ndarray, model_roi: np.ndarray, mask_roi: np.ndarray) -> float:
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


def _roi_correlations(
    target: np.ndarray,
    model: np.ndarray,
    loss_mask: np.ndarray,
    panel_slices: List,
) -> List[float]:
    corrs: List[float] = []
    for pid, bbox in panel_slices:
        x0, x1, y0, y1 = bbox
        roi_mask = loss_mask[int(pid), y0:y1, x0:x1]
        if not np.any(roi_mask):
            continue
        data_roi = target[int(pid), y0:y1, x0:x1]
        model_roi = model[int(pid), y0:y1, x0:x1]
        corrs.append(_masked_roi_corr(data_roi, model_roi, roi_mask))
    return corrs


@pytest.fixture
def stage_a_smoke_result(
    hkl_data,
    refgeom_dataload,
    smoke_sigma_source,
):
    """
    Stage A-only refinement (nearest-neighbor HKL) for DB-AT-028/029 gates.
    Uses build_mapping_stage_a_context to align HKL/calibration/inputs with mapping forward stack.

    Data dependencies:
        - Reuses the same ``refgeom_dataload`` inputs (geometry, mask, HKL
          override, calibration path) that DB-AT-028/029 are testing. Any change
          to the DataLoad fixture propagates here automatically.
        - Mapping context diagnostics MUST reflect those inputs (HKL source,
          calibration path, sigma provenance) before computing ROI correlations.
        - HKL sampling is nearest-neighbor (`enable_hkl_interpolation=False`)
          per the Stage-A spec; interpolated grids would violate DB-AT-028/029.
    """
    # Build mapping context for unified HKL/calibration/inputs
    device_obj = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    device = str(device_obj)

    # TOOLING-VIS-001: Pass through apply_calibration_n_cells from fixture
    apply_n_cells = getattr(refgeom_dataload, 'apply_calibration_n_cells', True)

    mapping_context = build_mapping_stage_a_context(
        refgeom_dataload,
        default_sigma_readout=3.0,
        device=device,
        apply_calibration_n_cells=apply_n_cells,
    )

    # Use mapping_context.inputs directly (TOOLING-VIS-001 alignment requirement)
    refinement_inputs = mapping_context.inputs

    # Extract HKL grid from the mapping context's original indices/amplitudes
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=mapping_context.hkl_indices,
        amplitudes=mapping_context.hkl_amplitudes,
        device=device_obj,
        halo=True,
    )

    # Determine HKL source from mapping context diagnostics
    hkl_source = mapping_context.diagnostics.get("hkl_source", "scaled.mtz")
    hkl_path = mapping_context.diagnostics.get("hkl_path", "scaled.mtz")
    hkl_count = len(mapping_context.hkl_indices) if hasattr(mapping_context, 'hkl_indices') else 0

    # Extract calibration metadata
    spot_scale_override_val = 1.0
    if mapping_context.calibration:
        spot_scale_override_val = float(mapping_context.calibration.get("spot_scale_override", 1.0))

    baseline_crystal = refgeom_dataload.Expt.crystal
    baseline_detector = refgeom_dataload.Expt.detector
    baseline_beam = refgeom_dataload.Expt.beam

    perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
        baseline_crystal, baseline_detector, baseline_beam
    )

    config = RefinementConfig(
        device=device,
        dtype=torch.float32,
        history_size=10,
        max_iter=20,
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        enable_hkl_interpolation=False,  # DB-AT-028/029 require nearest-neighbor HKL sampling
        enable_stage_b=False,
        enable_stage_c=False,
        calibration_metadata=mapping_context.calibration,
        sigma_readout_provenance=(
            "external_lookup" if smoke_sigma_source == "metadata" else "cli_override"
        ),
    )

    bragg_final, telemetry_dict = run_nanobrag_refinement(
        inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,
        use_engine_delegation=True,
    )

    telemetry = telemetry_dict["A"]
    chi_trace = telemetry.chi_squared_trace_full or []
    masked_pixels = telemetry.variance_floor_masked_pixels
    if masked_pixels is None:
        masked_pixels = int(np.count_nonzero(refinement_inputs.loss_mask))

    device_obj = torch.device(config.device)
    bragg_before = _build_final_bragg_from_stage_a_telemetry(
        telemetry,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        inputs=refinement_inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=device_obj,
        dtype=config.dtype,
        param_state="initial",
        baseline_crystal=baseline_crystal,
    )
    bragg_after = _build_final_bragg_from_stage_a_telemetry(
        telemetry,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        inputs=refinement_inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=device_obj,
        dtype=config.dtype,
        param_state="final",
        baseline_crystal=baseline_crystal,
    )

    # Compute log_scale_effective from telemetry.param_deltas per STAGEA-001
    log_scale_entry = telemetry.param_deltas.get("log_scale", {})
    log_scale_baseline_entry = telemetry.param_deltas.get("log_scale_baseline", {})

    log_scale_baseline = log_scale_baseline_entry.get("final") if isinstance(log_scale_baseline_entry, dict) else 0.0
    log_scale_init = log_scale_entry.get("initial") if isinstance(log_scale_entry, dict) else 0.0
    log_scale_final = log_scale_entry.get("final") if isinstance(log_scale_entry, dict) else 0.0

    # log_scale_effective = baseline + clamped delta
    log_scale_effective_init = log_scale_baseline + log_scale_init if log_scale_baseline is not None else log_scale_init
    log_scale_effective_final = log_scale_baseline + log_scale_final if log_scale_baseline is not None else log_scale_final

    # Compute bragg statistics for before/after
    bragg_before_mean = float(np.mean(bragg_before))
    bragg_before_std = float(np.std(bragg_before))
    bragg_before_max = float(np.max(bragg_before))

    bragg_after_mean = float(np.mean(bragg_after))
    bragg_after_std = float(np.std(bragg_after))
    bragg_after_max = float(np.max(bragg_after))

    # Compute ROI correlation baselines using mapping_context.inputs
    corrs_before = _roi_correlations(refinement_inputs.target, bragg_before, refinement_inputs.loss_mask, refinement_inputs.panel_slices)
    corrs_after = _roi_correlations(refinement_inputs.target, bragg_after, refinement_inputs.loss_mask, refinement_inputs.panel_slices)
    valid_corrs_before = [c for c in corrs_before if np.isfinite(c)]
    valid_corrs_after = [c for c in corrs_after if np.isfinite(c)]

    roi_cc_median_before = float(np.median(valid_corrs_before)) if valid_corrs_before else float("nan")
    roi_cc_median_after = float(np.median(valid_corrs_after)) if valid_corrs_after else float("nan")

    # Use mapping context's bragg_zero_iter for parity comparison (DB-AT-028/029 diagnostics)
    # Compute MASKED scale ratios per input.md requirement (masked mean for both Bragg and target)
    roi_cc_median_mapping = float("nan")
    scale_ratio_mapping_masked = float("nan")
    scale_ratio_mapping_unmasked = float("nan")
    mapping_forward_success = False
    try:
        bragg_mapping = mapping_context.bragg_zero_iter

        # Compute mapping ROI correlations using the SAME mapping_context.inputs
        corrs_mapping = _roi_correlations(
            mapping_context.inputs.target,
            bragg_mapping,
            mapping_context.inputs.loss_mask,
            mapping_context.inputs.panel_slices
        )
        valid_mapping = [c for c in corrs_mapping if np.isfinite(c)]
        roi_cc_median_mapping = float(np.median(valid_mapping)) if valid_mapping else float("nan")

        # Compute mapping scale ratio MASKED (using loss_mask for both Bragg and target)
        mean_target_masked = float(np.mean(mapping_context.inputs.target[mapping_context.inputs.loss_mask]))
        bragg_mapping_mean_masked = float(np.mean(bragg_mapping[mapping_context.inputs.loss_mask]))
        scale_ratio_mapping_masked = bragg_mapping_mean_masked / mean_target_masked if mean_target_masked > 1e-12 else float("inf")

        # Compute mapping scale ratio UNMASKED (for diagnostic comparison)
        mean_target_unmasked = float(np.mean(mapping_context.inputs.target))
        bragg_mapping_mean_unmasked = float(np.mean(bragg_mapping))
        scale_ratio_mapping_unmasked = bragg_mapping_mean_unmasked / mean_target_unmasked if mean_target_unmasked > 1e-12 else float("inf")

        mapping_forward_success = True
    except Exception:
        pass  # Leave mapping metrics as NaN on failure

    return {
        "telemetry": telemetry,
        "chi_trace": chi_trace,
        "masked_pixels": int(masked_pixels),
        "clamp_fraction": telemetry.variance_floor_clamp_fraction or 0.0,
        "bragg_before": bragg_before,
        "bragg_after": bragg_after,
        "inputs": refinement_inputs,
        "config": config,
        "bragg_final": bragg_final,
        "hkl_source": hkl_source,
        "hkl_path": hkl_path,
        "hkl_count": hkl_count,
        "spot_scale_override": spot_scale_override_val,
        "sigma_source": smoke_sigma_source,
        # Additional diagnostics per input.md Phase D.D
        "log_scale_effective_init": log_scale_effective_init,
        "log_scale_effective_final": log_scale_effective_final,
        "bragg_before_mean": bragg_before_mean,
        "bragg_before_std": bragg_before_std,
        "bragg_before_max": bragg_before_max,
        "bragg_after_mean": bragg_after_mean,
        "bragg_after_std": bragg_after_std,
        "bragg_after_max": bragg_after_max,
        "roi_cc_median_before": roi_cc_median_before,
        "roi_cc_median_after": roi_cc_median_after,
        "roi_cc_median_mapping": roi_cc_median_mapping,
        "scale_ratio_mapping_masked": scale_ratio_mapping_masked,
        "scale_ratio_mapping_unmasked": scale_ratio_mapping_unmasked,
        "mapping_forward_success": mapping_forward_success,
        # Context objects for emitting mapping_context diagnostics (TOOLING-VIS-001)
        "mapping_context": mapping_context,
        "refgeom_dataload": refgeom_dataload,
    }


@pytest.mark.allow_metadata_sigma
def test_db_at_028_loss_scale_sanity(stage_a_smoke_result):
    """
    DB-AT-028 (docs/spec-db-conformance.md:280-318): chi²-per-pixel and clamp sanity.
    """
    telemetry = stage_a_smoke_result["telemetry"]
    chi_trace = stage_a_smoke_result["chi_trace"]
    masked_pixels = stage_a_smoke_result["masked_pixels"]
    clamp_fraction = stage_a_smoke_result["clamp_fraction"]

    assert chi_trace, "Stage A chi-squared trace missing"
    chi2_initial = chi_trace[0][1]
    chi2_final = chi_trace[-1][1]
    chi2_per_pixel_initial = chi2_initial / masked_pixels
    chi2_per_pixel_final = chi2_final / masked_pixels
    log_scale_entry = telemetry.param_deltas.get("log_scale", {})
    log_scale_baseline_entry = telemetry.param_deltas.get("log_scale_baseline", {})

    artifact_dir = _artifact_dir("DBAT028_ARTIFACT_DIR")

    # Emit mapping context diagnostics BEFORE assertions (TOOLING-VIS-001)
    emit_mapping_context_diagnostics(
        mapping_context=stage_a_smoke_result["mapping_context"],
        dataload=stage_a_smoke_result["refgeom_dataload"],
        output_path=artifact_dir / "mapping_context_fixture.json",
        bragg_model=stage_a_smoke_result["mapping_context"].bragg_zero_iter,
        stage_name="fixture_db_at_028",
    )

    # Extract calibration_path from mapping context diagnostics (TOOLING-VIS-001)
    calibration_path = stage_a_smoke_result["mapping_context"].diagnostics.get("calibration_path", None)

    # Persist metrics before assertions so artifacts exist even on failure
    metrics = {
        "chi2_per_pixel_initial": chi2_per_pixel_initial,
        "chi2_per_pixel_final": chi2_per_pixel_final,
        "variance_floor_clamp_fraction": clamp_fraction,
        "variance_floor_masked_pixels": masked_pixels,
        "variance_floor_masked_pixels_loss_mask": int(stage_a_smoke_result["inputs"].loss_mask.sum()),
        "chi_squared_trace_full": [[int(step), float(val)] for step, val in chi_trace],
        "device": stage_a_smoke_result["config"].device,
        "enable_hkl_interpolation": stage_a_smoke_result["config"].enable_hkl_interpolation,
        "log_scale_initial": log_scale_entry.get("initial") if isinstance(log_scale_entry, dict) else None,
        "log_scale_final": log_scale_entry.get("final") if isinstance(log_scale_entry, dict) else None,
        "log_scale_baseline": log_scale_baseline_entry.get("final") if isinstance(log_scale_baseline_entry, dict) else None,
        "log_scale_effective_init": stage_a_smoke_result.get("log_scale_effective_init"),
        "log_scale_effective_final": stage_a_smoke_result.get("log_scale_effective_final"),
        "bragg_before_mean": stage_a_smoke_result.get("bragg_before_mean"),
        "bragg_before_std": stage_a_smoke_result.get("bragg_before_std"),
        "bragg_before_max": stage_a_smoke_result.get("bragg_before_max"),
        "bragg_after_mean": stage_a_smoke_result.get("bragg_after_mean"),
        "bragg_after_std": stage_a_smoke_result.get("bragg_after_std"),
        "bragg_after_max": stage_a_smoke_result.get("bragg_after_max"),
        "roi_cc_median_before": stage_a_smoke_result.get("roi_cc_median_before"),
        "roi_cc_median_after": stage_a_smoke_result.get("roi_cc_median_after"),
        "hkl_source": stage_a_smoke_result.get("hkl_source"),
        "hkl_path": stage_a_smoke_result.get("hkl_path"),
        "hkl_count": stage_a_smoke_result.get("hkl_count"),
        "spot_scale_override": stage_a_smoke_result.get("spot_scale_override"),
        "calibration_path": calibration_path,
        "sigma_source": stage_a_smoke_result.get("sigma_source"),
        "roi_cc_median_mapping": stage_a_smoke_result.get("roi_cc_median_mapping"),
        "scale_ratio_mapping_masked": stage_a_smoke_result.get("scale_ratio_mapping_masked"),
        "scale_ratio_mapping_unmasked": stage_a_smoke_result.get("scale_ratio_mapping_unmasked"),
        "mapping_forward_success": stage_a_smoke_result.get("mapping_forward_success"),
        # SCALE-008 / TOOLING-VIS-001: Mapping-aware log-scale baseline telemetry
        "log_scale_baseline_source": telemetry.log_scale_baseline_source,
        "spot_scale_override_adjustment_factor": telemetry.spot_scale_override_adjustment_factor,
    }
    (artifact_dir / "db_at_028_metrics.json").write_text(json.dumps(metrics, indent=2))

    assert chi2_per_pixel_initial <= 1e2, f"chi²/pixel initial {chi2_per_pixel_initial:.3e} exceeds 1e2 bound"
    assert chi2_per_pixel_final <= 1e2, f"chi²/pixel final {chi2_per_pixel_final:.3e} exceeds 1e2 bound"
    assert chi2_per_pixel_final <= chi2_per_pixel_initial, "Stage A chi²/pixel increased after refinement"
    assert clamp_fraction < 0.5, f"variance_floor_clamp_fraction {clamp_fraction:.3f} too high"


@pytest.mark.allow_metadata_sigma
def test_db_at_029_structure_parity(stage_a_smoke_result):
    """
    DB-AT-029 (docs/spec-db-conformance.md:319-366): ROI structure parity vs data.
    """
    telemetry = stage_a_smoke_result["telemetry"]
    inputs = stage_a_smoke_result["inputs"]
    target = inputs.target
    loss_mask = inputs.loss_mask
    bragg_before = stage_a_smoke_result["bragg_before"]
    bragg_after = stage_a_smoke_result["bragg_after"]

    corrs_before = _roi_correlations(target, bragg_before, loss_mask, inputs.panel_slices)
    corrs_after = _roi_correlations(target, bragg_after, loss_mask, inputs.panel_slices)
    valid_before = [c for c in corrs_before if np.isfinite(c)]
    valid_after = [c for c in corrs_after if np.isfinite(c)]

    assert valid_before, "No valid ROI correlations computed for bragg_before"
    assert valid_after, "No valid ROI correlations computed for bragg_after"

    median_before = float(np.median(valid_before))
    median_after = float(np.median(valid_after)) if valid_after else float("nan")
    mean_target = float(np.mean(target[loss_mask]))
    mean_model_before = float(np.mean(bragg_before[loss_mask]))
    scale_ratio_before = mean_model_before / mean_target if mean_target > 0 else float("inf")
    log_scale_entry = telemetry.param_deltas.get("log_scale", {})
    log_scale_baseline_entry = telemetry.param_deltas.get("log_scale_baseline", {})

    artifact_dir = _artifact_dir("DBAT029_ARTIFACT_DIR")

    # Emit mapping context diagnostics BEFORE assertions (TOOLING-VIS-001)
    emit_mapping_context_diagnostics(
        mapping_context=stage_a_smoke_result["mapping_context"],
        dataload=stage_a_smoke_result["refgeom_dataload"],
        output_path=artifact_dir / "mapping_context_fixture.json",
        bragg_model=stage_a_smoke_result["mapping_context"].bragg_zero_iter,
        stage_name="fixture_db_at_029",
    )

    # Extract calibration_path from mapping context diagnostics (TOOLING-VIS-001)
    calibration_path = stage_a_smoke_result["mapping_context"].diagnostics.get("calibration_path", None)

    metrics = {
        "median_corr_before": median_before,
        "median_corr_after": median_after,
        "scale_ratio_before": scale_ratio_before,
        "n_rois": len(valid_before),
        "device": stage_a_smoke_result["config"].device,
        "enable_hkl_interpolation": stage_a_smoke_result["config"].enable_hkl_interpolation,
        "variance_floor_masked_pixels": int(stage_a_smoke_result["telemetry"].variance_floor_masked_pixels or 0),
        "variance_floor_masked_pixels_loss_mask": int(loss_mask.sum()),
        "log_scale_initial": log_scale_entry.get("initial") if isinstance(log_scale_entry, dict) else None,
        "log_scale_final": log_scale_entry.get("final") if isinstance(log_scale_entry, dict) else None,
        "log_scale_baseline": log_scale_baseline_entry.get("final") if isinstance(log_scale_baseline_entry, dict) else None,
        "log_scale_effective_init": stage_a_smoke_result.get("log_scale_effective_init"),
        "log_scale_effective_final": stage_a_smoke_result.get("log_scale_effective_final"),
        "bragg_before_mean": stage_a_smoke_result.get("bragg_before_mean"),
        "bragg_before_std": stage_a_smoke_result.get("bragg_before_std"),
        "bragg_before_max": stage_a_smoke_result.get("bragg_before_max"),
        "bragg_after_mean": stage_a_smoke_result.get("bragg_after_mean"),
        "bragg_after_std": stage_a_smoke_result.get("bragg_after_std"),
        "bragg_after_max": stage_a_smoke_result.get("bragg_after_max"),
        "hkl_source": stage_a_smoke_result.get("hkl_source"),
        "hkl_path": stage_a_smoke_result.get("hkl_path"),
        "hkl_count": stage_a_smoke_result.get("hkl_count"),
        "spot_scale_override": stage_a_smoke_result.get("spot_scale_override"),
        "calibration_path": calibration_path,
        "sigma_source": stage_a_smoke_result.get("sigma_source"),
        "roi_cc_median_mapping": stage_a_smoke_result.get("roi_cc_median_mapping"),
        "scale_ratio_mapping_masked": stage_a_smoke_result.get("scale_ratio_mapping_masked"),
        "scale_ratio_mapping_unmasked": stage_a_smoke_result.get("scale_ratio_mapping_unmasked"),
        "mapping_forward_success": stage_a_smoke_result.get("mapping_forward_success"),
        # SCALE-008 / TOOLING-VIS-001: Mapping-aware log-scale baseline telemetry
        "log_scale_baseline_source": telemetry.log_scale_baseline_source,
        "spot_scale_override_adjustment_factor": telemetry.spot_scale_override_adjustment_factor,
    }
    (artifact_dir / "db_at_029_metrics.json").write_text(json.dumps(metrics, indent=2))

    assert median_before >= 0.2, f"median ROI correlation before refinement {median_before:.3f} below 0.2 floor"
    assert median_after >= median_before - 0.05, (
        f"median ROI correlation after refinement {median_after:.3f} regressed by more than 0.05"
    )
    assert 1e-2 <= scale_ratio_before <= 1e2, (
        f"scale_ratio_before={scale_ratio_before:.3e} outside [1e-2, 1e2]"
    )
