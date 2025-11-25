import json
import os
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest
import torch

from dbex.nanobrag_bridge import (
    build_structure_factor_grid,
    load_calibration_metadata,
    load_refined_mtz,
)
from dbex.nanobrag_refinement import (
    RefinementConfig,
    _build_final_bragg_from_stage_a_telemetry,
    run_nanobrag_refinement,
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
    refinement_inputs,
    hkl_data,
    refgeom_dataload,
    smoke_sigma_source,
):
    """
    Stage A-only refinement (nearest-neighbor HKL) for DB-AT-028/029 gates.
    Reuses calibrated mapping metadata when available (config_torch.json).
    """
    hkl_grid, hkl_metadata = hkl_data
    hkl_source = "scaled.mtz"
    baseline_crystal = refgeom_dataload.Expt.crystal
    baseline_detector = refgeom_dataload.Expt.detector
    baseline_beam = refgeom_dataload.Expt.beam

    perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
        baseline_crystal, baseline_detector, baseline_beam
    )

    repo_root = Path(__file__).resolve().parents[2]
    calibration_path = repo_root / "tests" / "fixtures" / "golden_data" / "simple_cubic" / "config_torch.json"
    # Prefer calibrated mapping payload to align Stage A scale; fallback to None if absent.
    calibration_metadata: Dict = {}
    if calibration_path.exists():
        try:
            calibration_metadata = load_calibration_metadata(calibration_path)
        except Exception:
            calibration_metadata = {}
    if not calibration_metadata:
        calibration_metadata = None
    device_obj = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    device = str(device_obj)

    if calibration_metadata:
        refined_mtz = (
            repo_root / "tests" / "fixtures" / "golden_data" / "simple_cubic" / "refined_structure_factors.mtz"
        )
        if refined_mtz.exists():
            try:
                refined_indices, refined_amplitudes = load_refined_mtz(refined_mtz)
                hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
                    indices=refined_indices,
                    amplitudes=refined_amplitudes,
                    device=device_obj,
                    halo=True,
                )
                hkl_source = "refined_structure_factors.mtz"
            except Exception:
                hkl_source = "scaled.mtz"
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
        calibration_metadata=calibration_metadata or None,
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
        "hkl_source": stage_a_smoke_result.get("hkl_source"),
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
        "hkl_source": stage_a_smoke_result.get("hkl_source"),
    }
    (artifact_dir / "db_at_029_metrics.json").write_text(json.dumps(metrics, indent=2))

    assert median_before >= 0.2, f"median ROI correlation before refinement {median_before:.3f} below 0.2 floor"
    assert median_after >= median_before - 0.05, (
        f"median ROI correlation after refinement {median_after:.3f} regressed by more than 0.05"
    )
    assert 1e-2 <= scale_ratio_before <= 1e2, (
        f"scale_ratio_before={scale_ratio_before:.3e} outside [1e-2, 1e2]"
    )
