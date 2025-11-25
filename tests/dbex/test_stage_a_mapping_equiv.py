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

    # Run engine-delegation zero-point probe (DB-AT-027)
    result = run_engine_zero_point_probe(
        dataload,
        device_str="cpu",
        sigma_source=sigma_source,
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
    artifact_dir = os.environ.get("DBAT027_ARTIFACT_DIR")
    if artifact_dir:
        artifact_path = Path(artifact_dir)
        artifact_path.mkdir(parents=True, exist_ok=True)

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
