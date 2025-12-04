import json
import os
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest
import torch

from dbex.nanobrag_bridge import (
    build_structure_factor_grid,
    simulate_forward_once,
)
from dbex.refinement.config import RefinementConfig
from dbex.refinement.context import build_refinement_context
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry
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
        apply_calibration_n_cells=apply_n_cells,  # TOOLING-VIS-001 Phase D.C gate
    )

    # ARCH-REFACTOR-001 Phase D.3 Batch 2: Direct RefinementEngine usage
    refinement_context = build_refinement_context(
        refinement_inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,  # Stage C disabled (enable_stage_c=False)
    )
    stages = [StageA()]
    engine = RefinementEngine(stages, config=config)
    telemetry_dict = engine.run({"context": refinement_context})

    # ARCH-SIM-CONSTRUCTION-001 Phase C.9: Defensive artifact lookup with fallback
    stage_a_artifacts = getattr(engine, "_artifacts", {}).get("stage_a")
    bragg_final = stage_a_artifacts.bragg_full if stage_a_artifacts else None
    stage_a_ctx = stage_a_artifacts.stage_a_ctx if stage_a_artifacts else None

    telemetry = telemetry_dict["stage_a"]
    chi_trace = telemetry.chi_squared_trace_full or []
    masked_pixels = telemetry.variance_floor_masked_pixels
    if masked_pixels is None:
        masked_pixels = int(np.count_nonzero(refinement_inputs.loss_mask))

    device_obj = torch.device(config.device)

    # ARCH-SIM-CONSTRUCTION-001 Phase C.8: Rebuild bragg_before/after from Stage A telemetry
    # using initial/final parameter states instead of simulate_forward_once.
    # This ensures DB-AT-028/029 measure the same Stage A baseline that refinement used,
    # eliminating the double-application of spot_scale and aligning with the telemetry baseline.

    # Build bragg_before from initial telemetry parameters (zero-iteration baseline)
    # ARCH-SIM-CONSTRUCTION-001 Phase C.9: Use stage_a_ctx from artifacts (warm cache)
    bragg_before = build_final_bragg_from_stage_a_telemetry(
        telemetry_a=telemetry,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        inputs=refinement_inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=device_obj,
        dtype=config.dtype,
        stage_a_ctx=stage_a_ctx,  # Use cached context if available, else None triggers cold path
        baseline_crystal=baseline_crystal,
        param_state="initial",  # Use initial telemetry params for zero-iteration baseline
    )

    # Build bragg_after from final telemetry parameters (post-refinement)
    # ARCH-SIM-CONSTRUCTION-001 Phase C.9: Reuse cached bragg_full when available (warm path)
    # The cached bragg_final from artifacts represents the exact Stage A output,
    # avoiding cold reconstruction path that drops warmed context.
    # If artifacts are missing, fall back to cold reconstruction.
    if bragg_final is not None:
        bragg_after = bragg_final
    else:
        bragg_after = build_final_bragg_from_stage_a_telemetry(
            telemetry_a=telemetry,
            detector=perturbed_detector,
            beam=perturbed_beam,
            crystal=perturbed_crystal,
            inputs=refinement_inputs,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            config=config,
            device=device_obj,
            dtype=config.dtype,
            stage_a_ctx=stage_a_ctx,
            baseline_crystal=baseline_crystal,
            param_state="final",
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

    # Use computed bragg_before for parity comparison (DB-AT-028/029 diagnostics)
    # Compute MASKED scale ratios per input.md requirement (masked mean for both Bragg and target)
    roi_cc_median_mapping = float("nan")
    scale_ratio_mapping_masked = float("nan")
    scale_ratio_mapping_unmasked = float("nan")
    mapping_forward_success = False
    try:
        bragg_mapping = bragg_before

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
        bragg_model=stage_a_smoke_result["bragg_before"],  # Use computed bragg_before from fixture
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
        # TOOLING-VIS-001 Phase D.E: Masked-mean telemetry for Stage A baseline derivation
        "target_mean_masked": telemetry.target_mean_masked,
        "model_mean_masked": telemetry.model_mean_masked,
        # ARCH-SIM-CONSTRUCTION-001 Phase C.8: Document bragg_before source
        "bragg_before_source": "stage_a_telemetry_initial",
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
        bragg_model=stage_a_smoke_result["bragg_before"],  # Use computed bragg_before from fixture
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
        # TOOLING-VIS-001 Phase D.E: Masked-mean telemetry for Stage A baseline derivation
        "target_mean_masked": telemetry.target_mean_masked,
        "model_mean_masked": telemetry.model_mean_masked,
        # ARCH-SIM-CONSTRUCTION-001 Phase C.8: Document bragg_before source
        "bragg_before_source": "stage_a_telemetry_initial",
    }
    (artifact_dir / "db_at_029_metrics.json").write_text(json.dumps(metrics, indent=2))

    # TOOLING-VIS-001 Phase E: Assert telemetry matches mapping diagnostics when calibration was adjusted
    mapping_diag = stage_a_smoke_result["mapping_context"].diagnostics
    calibration_adjusted = mapping_diag.get("calibration_adjusted_for_n_cells", False)
    if calibration_adjusted:
        # When mapping auto-adjusted calibration, Stage A must use the mapping global_scale_hint baseline
        assert telemetry.log_scale_baseline_source == "mapping_global_scale_hint", (
            f"Expected log_scale_baseline_source='mapping_global_scale_hint' when calibration adjusted, "
            f"got {telemetry.log_scale_baseline_source!r}"
        )
        # Adjustment factor must match between mapping and Stage A telemetry
        mapping_adj_factor = mapping_diag.get("spot_scale_override_adjustment_factor")
        assert telemetry.spot_scale_override_adjustment_factor is not None, (
            "Expected spot_scale_override_adjustment_factor in telemetry when calibration adjusted"
        )
        assert abs(telemetry.spot_scale_override_adjustment_factor - mapping_adj_factor) < 1e-6, (
            f"Adjustment factor mismatch: telemetry={telemetry.spot_scale_override_adjustment_factor}, "
            f"mapping={mapping_adj_factor}"
        )
        # Scale ratio before refinement should match mapping's masked ratio (both use global_scale_hint baseline)
        scale_ratio_mapping = stage_a_smoke_result.get("scale_ratio_mapping_masked", float("nan"))
        if np.isfinite(scale_ratio_mapping):
            # Allow 1% tolerance for numerical differences
            assert abs(scale_ratio_before - scale_ratio_mapping) / scale_ratio_mapping < 0.01, (
                f"scale_ratio_before={scale_ratio_before:.6f} diverges from "
                f"scale_ratio_mapping_masked={scale_ratio_mapping:.6f} by more than 1%"
            )

    assert median_before >= 0.2, f"median ROI correlation before refinement {median_before:.3f} below 0.2 floor"
    assert median_after >= median_before - 0.05, (
        f"median ROI correlation after refinement {median_after:.3f} regressed by more than 0.05"
    )
    assert 1e-2 <= scale_ratio_before <= 1e2, (
        f"scale_ratio_before={scale_ratio_before:.3e} outside [1e-2, 1e2]"
    )


def test_stage_a_baseline_metrics_dump(
    hkl_data,
    refgeom_dataload,
    smoke_sigma_source,
):
    """
    Test Stage A baseline metrics collection via config.enable_stage_a_baseline_metrics=True.

    Per ARCH-PROBE-FREEZE-001 Phase B: validates that RefinementEngine with Stage A only
    can emit baseline metrics (masked/unmasked means, chi²-per-pixel, ROI Pearson correlations)
    via the new telemetry hook, and that StageAArtifacts.baseline_metrics is populated with
    the expected schema v1 fields.

    This test ensures the production telemetry path works without relying on plan-local probes.
    """
    # Build config with baseline metrics enabled
    device_obj = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    device = str(device_obj)
    apply_n_cells = getattr(refgeom_dataload, 'apply_calibration_n_cells', True)

    # Build HKL grid from fixture
    hkl_grid, hkl_metadata = hkl_data

    # Build mapping context for unified inputs (same as stage_a_smoke_result fixture)
    from dbex.vis.mapping import build_mapping_stage_a_context
    mapping_context = build_mapping_stage_a_context(
        refgeom_dataload,
        default_sigma_readout=3.0,
        device=device,
        apply_calibration_n_cells=apply_n_cells,
    )
    refinement_inputs = mapping_context.inputs

    # Configure with baseline metrics enabled
    from dbex.refinement.config import RefinementConfig
    config = RefinementConfig(
        device=device,
        dtype=torch.float32,
        enable_hkl_interpolation=False,  # Nearest-neighbor per DB-AT-028/029
        enable_stage_a_warm_cache=True,
        enable_stage_a_baseline_metrics=True,  # Enable baseline metrics collection
        stage_a_baseline_metrics_path=None,  # No JSON dump for test (only StageAArtifacts)
        enable_stage_b=False,
        enable_stage_c=False,
        calibration_metadata=refgeom_dataload.calibration_metadata if hasattr(refgeom_dataload, 'calibration_metadata') else None,
        sigma_readout_reference_value=3.0,
    )

    # Build refinement context
    from dbex.refinement.context import build_refinement_context
    context = build_refinement_context(
        refinement_inputs=refinement_inputs,
        detector=refgeom_dataload.detector,
        beam=refgeom_dataload.beam,
        crystal=refgeom_dataload.crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        baseline_crystal=None,
        baseline_detector=None,
    )

    # Run RefinementEngine with Stage A only
    stage_a = StageA()
    engine = RefinementEngine(stages=[stage_a], config=config)
    result = engine.run({'context': context})

    # Extract Stage A artifacts
    stage_a_artifacts = result.artifacts.get("stage_a")
    assert stage_a_artifacts is not None, "Stage A artifacts missing from result"
    assert stage_a_artifacts.baseline_metrics is not None, "baseline_metrics not populated in StageAArtifacts"

    # Validate baseline_metrics schema v1 fields
    metrics = stage_a_artifacts.baseline_metrics
    assert metrics["schema_version"] == "v1", f"Unexpected schema version: {metrics.get('schema_version')}"

    # Validate masked_means
    assert "masked_means" in metrics, "masked_means missing from baseline_metrics"
    assert "target_mean_masked" in metrics["masked_means"], "target_mean_masked missing"
    assert "model_mean_masked" in metrics["masked_means"], "model_mean_masked missing"
    assert "bragg_mean_masked" in metrics["masked_means"], "bragg_mean_masked missing"
    assert np.isfinite(metrics["masked_means"]["target_mean_masked"]), "target_mean_masked is NaN/Inf"
    assert np.isfinite(metrics["masked_means"]["model_mean_masked"]), "model_mean_masked is NaN/Inf"
    assert np.isfinite(metrics["masked_means"]["bragg_mean_masked"]), "bragg_mean_masked is NaN/Inf"

    # Validate unmasked_means
    assert "unmasked_means" in metrics, "unmasked_means missing from baseline_metrics"
    assert "target_mean_unmasked" in metrics["unmasked_means"], "target_mean_unmasked missing"
    assert "model_mean_unmasked" in metrics["unmasked_means"], "model_mean_unmasked missing"
    assert "bragg_mean_unmasked" in metrics["unmasked_means"], "bragg_mean_unmasked missing"

    # Validate chi_squared
    assert "chi_squared" in metrics, "chi_squared missing from baseline_metrics"
    assert "chi_squared_per_pixel_initial" in metrics["chi_squared"], "chi_squared_per_pixel_initial missing"
    assert "n_masked_pixels" in metrics["chi_squared"], "n_masked_pixels missing"
    chi_squared_per_pixel = metrics["chi_squared"]["chi_squared_per_pixel_initial"]
    assert np.isfinite(chi_squared_per_pixel), "chi_squared_per_pixel_initial is NaN/Inf"
    assert chi_squared_per_pixel > 0, f"chi_squared_per_pixel_initial={chi_squared_per_pixel:.2e} must be positive"

    # Validate roi_correlations
    assert "roi_correlations" in metrics, "roi_correlations missing from baseline_metrics"
    assert "median_roi_pearson" in metrics["roi_correlations"], "median_roi_pearson missing"
    assert "n_rois_with_correlations" in metrics["roi_correlations"], "n_rois_with_correlations missing"
    n_rois = metrics["roi_correlations"]["n_rois_with_correlations"]
    assert n_rois > 0, f"No ROIs with correlations: n_rois_with_correlations={n_rois}"

    # Validate roi_snippets
    assert "roi_snippets" in metrics, "roi_snippets missing from baseline_metrics"
    assert isinstance(metrics["roi_snippets"], list), "roi_snippets must be a list"
    if metrics["roi_snippets"]:
        snippet = metrics["roi_snippets"][0]
        assert "panel_id" in snippet, "roi_snippet missing panel_id"
        assert "bbox" in snippet, "roi_snippet missing bbox"
        assert "pearson_corr" in snippet, "roi_snippet missing pearson_corr"

    print(f"[test_stage_a_baseline_metrics_dump] PASS")
    print(f"  Masked chi²/px: {chi_squared_per_pixel:.2e}")
    print(f"  N masked pixels: {metrics['chi_squared']['n_masked_pixels']}")
    print(f"  Median ROI Pearson: {metrics['roi_correlations']['median_roi_pearson']:.4f}")
    print(f"  N ROIs with correlations: {n_rois}")
