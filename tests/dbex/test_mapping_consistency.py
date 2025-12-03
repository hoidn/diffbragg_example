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

from dbex.data_load import DataLoad, _load_external_lookup_sigma_map
from dbex.refinement.inputs import prepare_refinement_inputs
from dbex.nanobrag_bridge import (
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
    def canonical_assets(self, smoke_sigma_source):
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
        metadata_expt = repo_root / "sp.proc" / "idx-0000_sigma_metadata.expt"
        metadata_tiles = metadata_expt.with_suffix(".sigma_tiles.pkl")

        # Prefer refined geometry, fallback to legacy (SCALE-004)
        has_refined_geometry = refined_expt.exists() and refined_refl.exists()
        using_metadata_sigma = smoke_sigma_source == "metadata"
        if using_metadata_sigma:
            missing_metadata = [
                str(path)
                for path in (metadata_expt, metadata_tiles)
                if not path.exists()
            ]
            if missing_metadata:
                pytest.skip(
                    "Metadata sigma source requested but required assets are missing: "
                    f"{missing_metadata}. Run "
                    "plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py "
                    "to regenerate sp.proc/idx-0000_sigma_metadata.{expt,sigma_tiles.pkl}."
                )
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

        if using_metadata_sigma:
            from dxtbx.model import ExperimentList

            metadata_expts = ExperimentList.from_file(str(metadata_expt))
            metadata_imageset = metadata_expts[0].imageset if len(metadata_expts) > 0 else None
            sigma_map, sigma_meta = _load_external_lookup_sigma_map(
                metadata_imageset,
                dl.data.shape,
            )
            if sigma_map is None:
                pytest.skip(
                    "Metadata sigma source requested but metadata experiment lacks external_lookup tiles. "
                    "Regenerate sp.proc/idx-0000_sigma_metadata.{expt,sigma_tiles.pkl}."
                )
            dl.sigma_readout_map = sigma_map
            dl.sigma_readout_map_source = "external_lookup"
            dl.sigma_readout_map_metadata = sigma_meta

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
            "sigma_readout_map_source": getattr(dl, "sigma_readout_map_source", None),
            "sigma_readout_map_metadata": getattr(dl, "sigma_readout_map_metadata", None),
            "sigma_readout_map": getattr(dl, "sigma_readout_map", None),
            "using_metadata_sigma": using_metadata_sigma,
        }

    @pytest.mark.db_at_024
    @pytest.mark.mapping
    @pytest.mark.allow_metadata_sigma
    def test_db_at_024_mapping_smoke(
        self,
        canonical_assets,
        artifact_dir,
        smoke_sigma_source,
    ):
        """
        DB-AT-024 smoke test: zero-iteration mapping consistency.

        Measures correlation and localization between torch Bragg output and
        background-subtracted data for K ROIs. Emits metrics JSON/CSV under
        $DBAT024_ARTIFACT_DIR.

        Thresholds per docs/spec-db-conformance.md:43-46:
        - Median correlation >= 0.2
        - Localization success rate >= 90%

        Latest metrics (2025-11-04T190041Z) with calibration + sample clipping:
        - corr_median: 0.621 (PASS)
        - localization_success_rate: 0.935 (PASS)
        - n_cells_applied: true
        - calibration: spot_scale_override=3.185e17, N_cells=[36,28,26]

        The sample clipping guard (SCALE-005) enables N_cells when beam_config
        (flux/exposure/beamsize) is forwarded to nanobrag_torch.Simulator,
        preventing intensity blow-up and achieving parity with canonical captures.
        """
        os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")

        # Import parity utilities
        from tests.fixtures.parity_loader import compute_parity_metrics

        dl = canonical_assets["dataload"]

        # Prepare refinement inputs
        if smoke_sigma_source == "metadata":
            sigma_map = canonical_assets.get("sigma_readout_map")
            sigma_map_source = canonical_assets.get("sigma_readout_map_source")
            if sigma_map is None or sigma_map_source != "external_lookup":
                pytest.skip(
                    "Metadata sigma source requested but DataLoad lacks an external_lookup "
                    "sigma_readout_map. Ensure sp.proc/idx-0000_sigma_metadata assets exist."
                )
            sigma_readout = np.asarray(sigma_map, dtype=np.float32)
            sigma_provenance = "external_lookup"
        else:
            sigma_readout = np.full_like(dl.data, 3.0, dtype=np.float32)
            sigma_provenance = "cli_override"

        inputs = prepare_refinement_inputs(
            data=dl.data,
            background_image=dl.background_image,
            trusted_mask=dl.trusted_mask,
            bbox=dl.bbox,
            pids=dl.pids,
            detector=dl.detector,
            adu_per_photon=None,  # ADU mode per DB-AT-024 baseline
            sigma_readout=sigma_readout,
            sigma_readout_provenance=sigma_provenance,
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
            hkl_source = "refined"
            hkl_path = str(canonical_assets["paths"].get("refined_mtz", ""))
        else:
            hkl_indices = dl.F.indices()
            hkl_amplitudes = dl.F.data()
            hkl_source = "raw"
            hkl_path = str(canonical_assets["paths"].get("mtz", ""))

        # Run zero-iteration forward simulation with DiffBragg calibration
        # Pass calibration dict to simulate_forward_once so beam flux/beamsize/exposure
        # and crystal N_cells flow through to nanobrag_torch configs per input.md Do Now step 4
        # MAP-SCALE-004: Pass hkl_source and hkl_path for telemetry
        bragg, diagnostics = simulate_forward_once(
            inputs=inputs,
            detector=dl.detector,
            beam=dl.beam,
            crystal=dl.crystal,
            experiment=dl.Expt,
            hkl_indices=hkl_indices,
            hkl_amplitudes=hkl_amplitudes,
            calibration=calibration,
            hkl_source=hkl_source,
            hkl_path=hkl_path,
            device="cpu",
        )
        assert "chi_squared" in diagnostics, "simulate_forward_once must emit chi_squared telemetry"
        assert diagnostics["chi_squared"] > 0, "chi_squared should be positive"
        assert "sigma_floor_value" in diagnostics, "sigma_floor_value missing from diagnostics"
        assert diagnostics["sigma_floor_value"] > 0, "sigma_floor_value must be > 0"
        clamp_fraction = diagnostics.get("variance_floor_clamp_fraction")
        assert clamp_fraction is not None, "variance_floor_clamp_fraction missing from diagnostics"
        assert 0.0 <= clamp_fraction <= 1.0, "variance_floor_clamp_fraction must be within [0, 1]"
        assert diagnostics.get("sigma_readout_provenance") == sigma_provenance, (
            f"Expected sigma_readout_provenance={sigma_provenance} but got "
            f"{diagnostics.get('sigma_readout_provenance')}"
        )

        sigma_reference_value = diagnostics.get("sigma_readout_reference_value")
        assert sigma_reference_value is not None, "sigma_readout_reference_value missing from diagnostics"
        assert sigma_reference_value > 0, "sigma_readout_reference_value must be positive"

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
            "hkl_source": hkl_source,  # Legacy field (kept for backward compat)
            "using_refined_geometry": canonical_assets.get("using_refined_geometry", False),
            "geometry_source": str(canonical_assets["paths"]["expt"]),
            "calibration": {
                "spot_scale_override": float(spot_scale_override),
                "sqrt_spot_scale": float(np.sqrt(spot_scale_override)),
                "beam_flux": calibration["beam_flux"],
                "beam_exposure": calibration["beam_exposure"],
                "beamsize_mm": calibration.get("beamsize_mm"),
                "N_cells": calibration.get("N_cells"),
                "n_cells_applied": diagnostics.get("n_cells_applied", False),  # input.md Do Now step 5
                "source": "tests/fixtures/golden_data/simple_cubic/config_torch.json",
            },
            "hkl_telemetry": diagnostics.get("hkl_telemetry", {}),  # MAP-SCALE-004
            "canonical_loss": {
                "chi_squared": float(diagnostics["chi_squared"]),
                "sigma_floor_value": float(diagnostics["sigma_floor_value"]),
                "variance_floor_clamp_fraction": float(clamp_fraction),
            },
            "sigma_readout": {
                "provenance": diagnostics.get("sigma_readout_provenance"),
                "reference_value": float(sigma_reference_value),
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

        # MAP-SCALE-004: Assert telemetry fields are present and correct
        assert "hkl_telemetry" in diagnostics, (
            "DB-AT-024 FAILED: Missing hkl_telemetry in diagnostics. "
            "MAP-SCALE-004 requires structure-factor telemetry to enforce refined MTZ usage."
        )
        hkl_telemetry = diagnostics["hkl_telemetry"]
        assert "hkl_source" in hkl_telemetry, "Missing hkl_source in hkl_telemetry"
        assert "hkl_n_reflections" in hkl_telemetry, "Missing hkl_n_reflections in hkl_telemetry"
        assert "hkl_mean_amplitude" in hkl_telemetry, "Missing hkl_mean_amplitude in hkl_telemetry"
        assert "hkl_path" in hkl_telemetry, "Missing hkl_path in hkl_telemetry"

        # MAP-SCALE-004: When canonical assets provide refined structure factors, telemetry must reflect this
        if refined_hkl is not None:
            assert hkl_telemetry["hkl_source"] == "refined", (
                f"DB-AT-024 FAILED: Refined structure factors provided but telemetry reports "
                f"hkl_source='{hkl_telemetry['hkl_source']}'. Expected 'refined'. "
                f"This indicates a regression in structure-factor loading per SCALE-003/SCALE-004."
            )
            print(f"  ✓ Telemetry confirms refined structure factors: "
                  f"n_reflections={hkl_telemetry['hkl_n_reflections']}, "
                  f"mean_amplitude={hkl_telemetry['hkl_mean_amplitude']:.3e}")
        else:
            print(f"  ⚠ Using raw structure factors (canonical assets lack refined MTZ)")

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
