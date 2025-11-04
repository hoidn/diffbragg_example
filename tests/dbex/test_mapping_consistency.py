"""
DB-AT-024 Mapping Consistency Guard

Acceptance test for zero-iteration forward mapping between DIALS geometry and
nanobrag_torch detector/crystal configs.

Per docs/spec-db-conformance.md:43-46:
- Median ROI correlation >= 0.2 between torch Bragg output and data-background
- Localization success rate >= 90% (brightest pixel within central half-box)

Test emits diagnostic artifacts (metrics JSON/CSV, optional overlays) under
$DBAT024_ARTIFACT_DIR for parity debugging per docs/spec-db-tracing.md.

Environment flags:
- KMP_DUPLICATE_LIB_OK=TRUE (required for nanobrag_torch on some platforms)
- NANOBRAGG_DISABLE_COMPILE=1 (recommended for deterministic CPU execution)
- DBAT024_ARTIFACT_DIR (required for artifact emission)

Example:
    DBAT024_ARTIFACT_DIR=plans/active/DB-AT-024/reports/2025-11-04T070000Z \
    KMP_DUPLICATE_LIB_OK=TRUE \
    pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
"""

import csv
import json
import os
from pathlib import Path
from statistics import median

import numpy as np
import pytest

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    prepare_refinement_inputs,
    simulate_forward_once,
    load_calibration_metadata,
    load_refined_mtz,
)


class TestDB_AT_024_Mapping:
    """
    DB-AT-024 acceptance test for mapping consistency between DIALS and nanobrag_torch.

    Validates zero-iteration forward simulation against canonical assets:
    - refGeom.expt, refGeom.refl, scaled.mtz, 747_mask.pkl

    Threshold enforcement via xfail with measured metrics documented in reason.
    """

    @pytest.fixture(scope="class")
    def artifact_dir(self):
        """Required artifact directory from environment."""
        artifact_dir = os.getenv("DBAT024_ARTIFACT_DIR")
        if not artifact_dir:
            pytest.skip("DBAT024_ARTIFACT_DIR not set; skipping DB_AT_024 selector")
        artifact_path = Path(artifact_dir)
        artifact_path.mkdir(parents=True, exist_ok=True)
        return artifact_path

    @pytest.fixture(scope="class")
    def canonical_assets(self):
        """Load canonical assets for DB-AT-024.

        Prefers DiffBragg-refined geometry (refined.expt/refined.refl) per SCALE-004.
        Falls back to legacy refGeom if refined assets are unavailable.
        """
        import argparse
        import warnings

        repo_root = Path.cwd()
        fixtures_root = repo_root / "tests" / "fixtures" / "golden_data" / "simple_cubic"

        # Define asset paths with refined geometry preference
        refined_expt = fixtures_root / "refined.expt"
        refined_refl = fixtures_root / "refined.refl"
        legacy_expt = repo_root / "refGeom.expt"
        legacy_refl = repo_root / "refGeom.refl"

        # Prefer refined geometry, fallback to legacy (SCALE-004)
        has_refined_geometry = refined_expt.exists() and refined_refl.exists()
        expt_path = refined_expt if has_refined_geometry else legacy_expt
        refl_path = refined_refl if has_refined_geometry else legacy_refl

        if not has_refined_geometry:
            warnings.warn(
                "Refined geometry not found in fixtures; falling back to legacy refGeom. "
                "This may prevent DB_AT_024 thresholds from passing per SCALE-004. "
                "Run golden generator with --fixtures to persist refined assets."
            )

        assets = {
            "mtz": repo_root / "scaled.mtz",
            "expt": expt_path,
            "refl": refl_path,
            "mask": repo_root / "747_mask.pkl",
            "calibration": fixtures_root / "config_torch.json",
            "refined_mtz": fixtures_root / "refined_structure_factors.mtz",
            "using_refined_geometry": has_refined_geometry,
        }

        # Check required assets exist
        required = ["mtz", "expt", "refl", "mask", "calibration"]
        missing = [name for name in required if not assets[name].exists()]
        if missing:
            pytest.skip(f"Missing canonical assets: {missing}")

        # Load via DataLoad with chosen geometry
        dataload_args = argparse.Namespace(
            mtzFile=str(assets["mtz"]),
            mtzCol="F,SIGF",
            exptName=str(assets["expt"]),
            exptIdx=0,
            reflName=str(assets["refl"]),
            maskFile=str(assets["mask"]),
        )
        dl = DataLoad(dataload_args)

        # Load calibration metadata
        calibration = load_calibration_metadata(assets["calibration"])

        # Load refined structure factors if available (MAP-SCALE-001)
        # Fallback to raw scaled.mtz if refined MTZ is missing
        refined_hkl = None
        if assets["refined_mtz"].exists():
            try:
                refined_indices, refined_amps = load_refined_mtz(assets["refined_mtz"])
                refined_hkl = (refined_indices, refined_amps)
            except Exception as e:
                # Log warning but continue with fallback
                import warnings
                warnings.warn(
                    f"Failed to load refined MTZ from {assets['refined_mtz']}: {e}. "
                    f"Falling back to raw scaled.mtz (may not meet thresholds)."
                )

        return {
            "dataload": dl,
            "paths": assets,
            "calibration": calibration,
            "refined_hkl": refined_hkl,
            "using_refined_geometry": has_refined_geometry,
        }

    @pytest.mark.db_at_024
    @pytest.mark.mapping
    def test_db_at_024_mapping_smoke(self, canonical_assets, artifact_dir):
        """
        DB-AT-024 smoke test: zero-iteration mapping consistency.

        Measures correlation and localization between torch Bragg output and
        background-subtracted data for K ROIs. Emits metrics JSON/CSV under
        $DBAT024_ARTIFACT_DIR.

        Current thresholds (provisional xfail until improved):
        - Median correlation >= 0.2
        - Localization success rate >= 90%

        Metrics from 2025-11-04T063053Z baseline:
        - corr_median: 0.0488
        - localization_success_rate: 0.0
        """
        os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")

        # Import parity utilities
        from tests.fixtures.parity_loader import compute_parity_metrics

        dl = canonical_assets["dataload"]

        # Prepare refinement inputs
        inputs = prepare_refinement_inputs(
            data=dl.data,
            background_image=dl.background_image,
            trusted_mask=dl.trusted_mask,
            bbox=dl.bbox,
            pids=dl.pids,
            detector=dl.detector,
            adu_per_photon=None,  # ADU mode per DB-AT-024 baseline
        )

        # Load calibration metadata (MAP-SCALE-001)
        # Contains spot_scale_override, beam flux/beamsize/exposure, and crystal N_cells
        calibration = canonical_assets["calibration"]
        spot_scale_override = calibration["spot_scale_override"]

        # Use refined structure factors if available (MAP-SCALE-001)
        # Otherwise fall back to raw MTZ (may not meet thresholds)
        refined_hkl = canonical_assets.get("refined_hkl")
        if refined_hkl is not None:
            hkl_indices, hkl_amplitudes = refined_hkl
            hkl_source = "refined_structure_factors.mtz"
        else:
            hkl_indices = dl.F.indices()
            hkl_amplitudes = dl.F.data()
            hkl_source = "scaled.mtz (raw, not refined)"

        # Run zero-iteration forward simulation with DiffBragg calibration
        # Pass calibration dict to simulate_forward_once so beam flux/beamsize/exposure
        # and crystal N_cells flow through to nanobrag_torch configs per input.md Do Now step 4
        bragg, diagnostics = simulate_forward_once(
            inputs=inputs,
            detector=dl.detector,
            beam=dl.beam,
            crystal=dl.crystal,
            experiment=dl.Expt,
            hkl_indices=hkl_indices,
            hkl_amplitudes=hkl_amplitudes,
            calibration=calibration,
            device="cpu",
        )

        # Compute per-ROI metrics
        roi_metrics = []
        correlations = []
        localizations = []

        for pid, (x0, x1, y0, y1) in inputs.panel_slices:
            pred = bragg[pid, y0:y1, x0:x1]
            targ = inputs.target[pid, y0:y1, x0:x1]
            mask = inputs.loss_mask[pid, y0:y1, x0:x1]

            roi_result = compute_parity_metrics(pred, targ, loss_mask=mask)
            roi_metrics.append(roi_result)

            if not np.isnan(roi_result.correlation):
                correlations.append(float(roi_result.correlation))
            if not np.isnan(roi_result.localization):
                localizations.append(float(roi_result.localization))

        # Aggregate metrics
        median_corr = median(correlations) if correlations else float("nan")
        localization_success_rate = (
            float(np.mean([loc == 1.0 for loc in localizations]))
            if localizations
            else float("nan")
        )

        summary_metrics = {
            "n_roi": len(roi_metrics),
            "corr_median": median_corr,
            "corr_min": float(min(correlations)) if correlations else float("nan"),
            "corr_max": float(max(correlations)) if correlations else float("nan"),
            "localization_mean": float(np.mean(localizations)) if localizations else float("nan"),
            "localization_success_rate": localization_success_rate,
            "global_scale_hint": inputs.global_scale_hint,
            "hkl_source": hkl_source,
            "using_refined_geometry": canonical_assets.get("using_refined_geometry", False),
            "geometry_source": str(canonical_assets["paths"]["expt"]),
            "calibration": {
                "spot_scale_override": float(spot_scale_override),
                "sqrt_spot_scale": float(np.sqrt(spot_scale_override)),
                "beam_flux": calibration["beam_flux"],
                "beam_exposure": calibration["beam_exposure"],
                "beamsize_mm": calibration.get("beamsize_mm"),
                "N_cells": calibration.get("N_cells"),
                "source": "tests/fixtures/golden_data/simple_cubic/config_torch.json",
            },
            "diagnostics": diagnostics,
        }

        # Write metrics JSON
        metrics_json_path = artifact_dir / "mapping_metrics.json"
        with open(metrics_json_path, "w") as f:
            json.dump(summary_metrics, f, indent=2)

        # Write per-ROI metrics CSV
        metrics_csv_path = artifact_dir / "mapping_metrics.csv"
        with open(metrics_csv_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "roi_idx",
                    "panel_id",
                    "x0",
                    "x1",
                    "y0",
                    "y1",
                    "correlation",
                    "rmse",
                    "mse",
                    "max_abs_diff",
                    "sum_ratio",
                    "localization",
                    "n_pixels",
                    "n_masked",
                ],
            )
            writer.writeheader()
            for idx, ((pid, (x0, x1, y0, y1)), m) in enumerate(
                zip(inputs.panel_slices, roi_metrics)
            ):
                writer.writerow(
                    {
                        "roi_idx": idx,
                        "panel_id": pid,
                        "x0": x0,
                        "x1": x1,
                        "y0": y0,
                        "y1": y1,
                        "correlation": m.correlation,
                        "rmse": m.rmse,
                        "mse": m.mse,
                        "max_abs_diff": m.max_abs_diff,
                        "sum_ratio": m.sum_ratio,
                        "localization": m.localization,
                        "n_pixels": m.n_pixels,
                        "n_masked": m.n_masked,
                    }
                )

        # Emit summary
        print(f"\n[DB-AT-024] Metrics summary:")
        print(f"  N ROIs: {summary_metrics['n_roi']}")
        print(f"  Median correlation: {median_corr:.4f}")
        print(f"  Localization success rate: {localization_success_rate:.2%}")
        print(f"  Global scale hint: {inputs.global_scale_hint:.2f}")
        print(f"  HKL source: {hkl_source}")
        print(f"  Geometry source: {summary_metrics['geometry_source']}")
        print(f"  Using refined geometry: {summary_metrics['using_refined_geometry']}")
        print(f"  Calibration: spot_scale_override={spot_scale_override:.3e}, sqrt={np.sqrt(spot_scale_override):.3e}")
        print(f"  Artifacts: {artifact_dir}/")

        # DB-AT-024 thresholds per docs/spec-db-conformance.md:43-46
        threshold_corr = 0.2
        threshold_loc = 0.90

        # Assert thresholds are met
        # MAP-SCALE-001: With refined structure factors + calibration, thresholds should pass
        assert median_corr >= threshold_corr, (
            f"DB-AT-024 FAILED: Median correlation {median_corr:.4f} below threshold {threshold_corr}. "
            f"HKL source: {hkl_source}. "
            f"Expected refined structure factors (refined_structure_factors.mtz) + calibration metadata "
            f"to align intensities per SCALE-003/SCALE-004 (docs/findings.md). "
            f"Metrics logged to {metrics_json_path}."
        )
        assert localization_success_rate >= threshold_loc, (
            f"DB-AT-024 FAILED: Localization success rate {localization_success_rate:.2%} below threshold {threshold_loc:.0%}. "
            f"HKL source: {hkl_source}. "
            f"Expected ≥90% ROIs to contain local maximum within central half-box per spec-db-conformance.md:45. "
            f"Metrics logged to {metrics_json_path}."
        )
