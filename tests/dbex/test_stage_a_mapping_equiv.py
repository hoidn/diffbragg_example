"""Stage A vs Mapping Equivalence Tests (DB-AT-027/028/029).

This module implements the DB-AT conformance selectors for Stage A zero-point
parity, loss-scale sanity, and intensity/structure parity vs experiment.

See docs/spec-db-conformance.md:200-280 for normative requirements.

Initiative: TOOLING-VIS-001 Phase D.B
Owner: Ralph (2025-11-24)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_db_at_027_zero_point_parity():
    """DB-AT-027: Stage A zero-point mapping equivalence.

    Ensures the Stage A zero-parameter forward model is equivalent to the
    DB-AT-024 mapping forward model at the same geometry, HKL grid, and
    calibration.

    Normative tolerances (docs/spec-db-conformance.md:201-239):
        - mean_abs_diff(bragg_stagea_zero - bragg_mapping) <= 1e-3
        - max_abs_diff(bragg_stagea_zero - bragg_mapping) <= 2.0e2
        - |chi2_rel_diff| <= 1e-3

    xfail status: Known Stage A zero-point miscalibration (STAGEA-001)
        - spot_scale_override not yet plumbed into Stage A engine
        - Expected to XPASS once Phase D.C calibration plumbing lands

    Environment:
        DBAT027_ARTIFACT_DIR: Optional artifact directory for metrics/env JSONs
        DBEX_SMOKE_SIGMA_SOURCE: Sigma readout provenance (default: metadata)
        DBEX_SMOKE_DETECTOR_SIZE: Detector size (full/small, not used by this test)
    """
    import json
    import subprocess

    # Lazy imports to avoid overhead when test is not selected
    from dbex.data_load import DataLoad
    from dbex.tools.stage_a_adam import build_dataload, run_engine_zero_point_probe

    # Construct DataLoad for canonical assets (prefers refined geometry)
    repo_root = Path(__file__).resolve().parents[2]
    dataload = build_dataload(repo_root)

    # Determine sigma source from environment (default: metadata)
    sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "metadata")
    detector_size = os.environ.get("DBEX_SMOKE_DETECTOR_SIZE", "full")

    # Resolve artifact directory (optional) for metrics + PNGs
    artifact_dir = os.environ.get("DBAT027_ARTIFACT_DIR")
    artifact_path = None
    if artifact_dir:
        artifact_path = Path(artifact_dir)
        artifact_path.mkdir(parents=True, exist_ok=True)

    # Run engine-delegation zero-point probe (DB-AT-027)
    result = run_engine_zero_point_probe(
        dataload,
        device_str="cpu",
        sigma_source=sigma_source,
        triptych_path=artifact_path / "db_at_027_zero_point_triptych.png" if artifact_path else None,
    )

    # Extract metrics
    mean_abs_diff = result["mean_abs_diff"]
    max_abs_diff = result["max_abs_diff"]
    chi2_rel_diff = result["chi2_rel_diff"]
    chi2_stagea = result["chi2_stagea"]
    chi2_mapping = result["chi2_mapping"]
    variance_floor_masked_pixels = result["variance_floor_masked_pixels"]
    roi_cc_samples = result["roi_cc_samples"]
    db_at_027_pass = result["db_at_027_pass"]

    # Emit artifact JSONs BEFORE assertions (so they're written even on xfail)
    if artifact_path:

        # db_at_027_metrics.json: Full result dict with all metrics
        metrics_json_path = artifact_path / "db_at_027_metrics.json"
        with metrics_json_path.open("w") as f:
            json.dump(result, f, indent=2)

        # db_at_027_env.json: Environment capture (sigma source, detector size, git head)
        try:
            git_head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            git_head = "unknown"

        env_json = {
            "sigma_source": sigma_source,
            "detector_size": detector_size,
            "git_head": git_head,
            "device": "cpu",
            "test_name": "test_db_at_027_zero_point_parity",
        }
        env_json_path = artifact_path / "db_at_027_env.json"
        with env_json_path.open("w") as f:
            json.dump(env_json, f, indent=2)

    # Log metrics for diagnosis (after artifact writing)
    print(f"\n=== DB-AT-027 Zero-Point Parity Metrics ===")
    print(f"mean_abs_diff: {mean_abs_diff:.6e} (tolerance: {result['tolerances']['mean_abs_diff']:.6e})")
    print(f"max_abs_diff: {max_abs_diff:.6e} (tolerance: {result['tolerances']['max_abs_diff']:.6e})")
    print(f"chi2_stagea: {chi2_stagea:.6e}")
    print(f"chi2_mapping: {chi2_mapping:.6e}")
    print(f"chi2_rel_diff: {chi2_rel_diff:.6e} (tolerance: {result['tolerances']['chi2_rel_diff']:.6e})")
    print(f"variance_floor_masked_pixels: {variance_floor_masked_pixels}")
    if roi_cc_samples:
        import statistics
        print(f"ROI CC median: {statistics.median(roi_cc_samples):.6f} (n={len(roi_cc_samples)})")
    print(f"db_at_027_pass: {db_at_027_pass}")
    if artifact_dir:
        print(f"Wrote artifacts: {artifact_path}")

    # Assert DB-AT-027 tolerances (fail fast with informative messages)
    assert mean_abs_diff <= result["tolerances"]["mean_abs_diff"], (
        f"DB-AT-027 FAIL: mean_abs_diff={mean_abs_diff:.6e} exceeds tolerance "
        f"{result['tolerances']['mean_abs_diff']:.6e}. "
        f"Stage A zero-point forward model diverges from mapping baseline. "
        f"Check calibration payload (spot_scale_override, flux, exposure, N_cells). "
        f"See docs/spec-db-conformance.md:201-239."
    )

    assert max_abs_diff <= result["tolerances"]["max_abs_diff"], (
        f"DB-AT-027 FAIL: max_abs_diff={max_abs_diff:.6e} exceeds tolerance "
        f"{result['tolerances']['max_abs_diff']:.6e}. "
        f"Large pixel-level discrepancies between Stage A and mapping forward models. "
        f"Check HKL grid halo, interpolation mode, and detector absorption parity. "
        f"See docs/spec-db-conformance.md:201-239."
    )

    assert abs(chi2_rel_diff) <= result["tolerances"]["chi2_rel_diff"], (
        f"DB-AT-027 FAIL: |chi2_rel_diff|={abs(chi2_rel_diff):.6e} exceeds tolerance "
        f"{result['tolerances']['chi2_rel_diff']:.6e}. "
        f"Stage A chi² on mapping stack diverges from mapping chi² baseline. "
        f"Variance-weighted loss implementation may differ between Stage A and mapping paths. "
        f"chi2_stagea={chi2_stagea:.6e}, chi2_mapping={chi2_mapping:.6e}. "
        f"See docs/spec-db-conformance.md:201-239 and PHYSICS-LOSS-001."
    )

    # If all assertions pass, db_at_027_pass should be True
    assert db_at_027_pass, (
        f"DB-AT-027 internal consistency error: individual tolerances passed but "
        f"db_at_027_pass={db_at_027_pass}. This indicates a logic bug in "
        f"run_engine_zero_point_probe."
    )


@pytest.mark.db_at_027
@pytest.mark.allow_metadata_sigma
@pytest.mark.xfail(
    reason=(
        "Stage A zero-point reconstruction currently does not reproduce the "
        "mapping baseline (STAGEA-001 baseline miscalibration); forward-only "
        "zero-point parity remains to be fixed."
    ),
    strict=False,
)
def test_db_at_027_zero_point_forward_only():
    """
    DB-AT-027 variant: zero-point forward parity only (no refinement steps).

    Compares the mapping zero-iteration Bragg stack from
    build_mapping_stage_a_context with the Stage A zero-point reconstruction
    built from telemetry at max_iter=0, using the same HKL grid, calibration,
    and inputs. Does not enforce any refinement behavior; it only checks that
    the Stage A forward model at zero deltas matches the mapping forward
    baseline.
    """
    import copy
    import json
    from pathlib import Path

    import numpy as np
    import torch

    from dbex.tools.stage_a_adam import build_dataload
    from dbex.vis.mapping import build_mapping_stage_a_context
    from dbex.nanobrag_bridge import build_structure_factor_grid
    from dbex.nanobrag_refinement import (
        RefinementConfig,
        run_nanobrag_refinement,
    )
    from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry

    repo_root = Path(__file__).resolve().parents[2]
    dataload = build_dataload(repo_root)

    # Build mapping context (DB-AT-024-style baseline) on CPU
    mapping_context = build_mapping_stage_a_context(
        dataload,
        default_sigma_readout=3.0,
        device="cpu",
    )

    # HKL grid mirrored from mapping context indices/amplitudes
    hkl_indices = mapping_context.hkl_indices
    hkl_amplitudes = mapping_context.hkl_amplitudes
    hkl_has_halo = bool(mapping_context.diagnostics.get("hkl_stats", {}).get("has_halo", False))
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device="cpu",
        halo=hkl_has_halo,
    )

    calibration = mapping_context.calibration or {}
    spot_scale_override = mapping_context.spot_scale_override
    if spot_scale_override is None and calibration:
        spot_scale_override = calibration.get("spot_scale_override")

    log_scale_baseline = None
    if spot_scale_override is not None:
        try:
            log_scale_baseline = float(np.log(np.sqrt(spot_scale_override)))
        except (TypeError, ValueError):
            log_scale_baseline = None

    # Stage A config with max_iter=0 (no refinement steps)
    config = RefinementConfig(
        device="cpu",
        max_iter=0,
        enable_stage_b=False,
        enable_stage_c=False,
        sigma_readout_provenance="metadata",
        calibration_metadata=mapping_context.calibration,
    )
    config.log_scale_baseline = log_scale_baseline

    # Run Stage A engine once to obtain telemetry at zero iterations
    bragg_full, telemetry_dict, _ = run_nanobrag_refinement(
        inputs=mapping_context.inputs,
        detector=dataload.detector,
        beam=dataload.beam,
        crystal=dataload.crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
    )

    telemetry_a = telemetry_dict.get("A")
    assert telemetry_a is not None, "Stage A telemetry missing in zero-point forward-only probe"

    # Force initial → final in telemetry so reconstruction uses zero deltas
    telemetry_a_zero = copy.deepcopy(telemetry_a)
    for key, val in telemetry_a_zero.param_deltas.items():
        if isinstance(val, dict) and "initial" in val and "final" in val:
            val["final"] = val["initial"]

    # Rebuild Stage A zero-point Bragg from telemetry
    device = torch.device("cpu")
    dtype = config.dtype
    bragg_stagea_zero = build_final_bragg_from_stage_a_telemetry(
        telemetry_a=telemetry_a_zero,
        detector=dataload.detector,
        beam=dataload.beam,
        crystal=dataload.crystal,
        inputs=mapping_context.inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=device,
        dtype=dtype,
    )

    bragg_mapping = mapping_context.bragg_zero_iter
    assert bragg_stagea_zero.shape == bragg_mapping.shape

    # Forward-only parity metrics
    diff = bragg_stagea_zero - bragg_mapping
    mean_abs_diff = float(np.abs(diff).mean())
    max_abs_diff = float(np.abs(diff).max())

    mean_abs_tol = 1e-3
    max_abs_tol = 2.0e2

    # Persist simple metrics alongside existing DB-AT-027 artifacts when requested
    artifact_dir = os.environ.get("DBAT027_ARTIFACT_DIR")
    if artifact_dir:
        artifact_path = Path(artifact_dir)
        artifact_path.mkdir(parents=True, exist_ok=True)
        payload = {
            "mean_abs_diff": mean_abs_diff,
            "max_abs_diff": max_abs_diff,
            "shape": list(bragg_mapping.shape),
        }
        (artifact_path / "db_at_027_forward_only_metrics.json").write_text(
            json.dumps(payload, indent=2)
        )

    assert mean_abs_diff <= mean_abs_tol, (
        f"DB-AT-027 forward-only FAIL: mean_abs_diff={mean_abs_diff:.6e} exceeds "
        f"tolerance {mean_abs_tol:.6e} for Stage A zero-point vs mapping baseline."
    )
    assert max_abs_diff <= max_abs_tol, (
        f"DB-AT-027 forward-only FAIL: max_abs_diff={max_abs_diff:.6e} exceeds "
        f"tolerance {max_abs_tol:.6e} for Stage A zero-point vs mapping baseline."
    )
