#!/usr/bin/env python3
"""
Probe script for TOOLING-VIS-001 Stage A mapping context.

This plan-local helper exercises the mapping-based Stage A context built by
``build_mapping_stage_a_context`` and compares per-ROI metrics against the
DB-AT-024 mapping semantics:

- Loads canonical assets via :class:`dbex.data_load.DataLoad` (refined
  geometry preferred, legacy refGeom fallback).
- Builds a mapping context using ``simulate_forward_once`` with refined
  structure factors + calibration when available.
- Computes per-ROI parity metrics (correlation, localization, etc.) using
  ``tests.fixtures.parity_loader.compute_parity_metrics``.
- Prints aggregate metrics (median correlation, localization success rate)
  and optionally checks them against reference DB-AT-024 metrics.

Usage (example):

    python plans/active/TOOLING-VIS-001/bin/probe_mapping_stage_a_context_metrics.py \\
        --reference-metrics plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z/mapping_metrics.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dbex.data_load import DataLoad  # type: ignore  # noqa: E402
from dbex.vis import build_mapping_stage_a_context  # type: ignore  # noqa: E402
from tests.fixtures.parity_loader import compute_parity_metrics  # type: ignore  # noqa: E402


def _build_dataload(repo_root: Path) -> DataLoad:
    """Construct a DataLoad instance for canonical assets (prefer refined geometry)."""
    fixtures_root = repo_root / "tests" / "fixtures" / "golden_data" / "simple_cubic"
    refined_expt = fixtures_root / "refined.expt"
    refined_refl = fixtures_root / "refined.refl"
    legacy_expt = repo_root / "refGeom.expt"
    legacy_refl = repo_root / "refGeom.refl"

    if refined_expt.exists() and refined_refl.exists():
        expt = refined_expt
        refl = refined_refl
    else:
        expt = legacy_expt
        refl = legacy_refl

    mtz = repo_root / "scaled.mtz"
    mask = repo_root / "747_mask.pkl"

    args = argparse.Namespace(
        exptName=str(expt),
        reflName=str(refl),
        exptIdx=0,
        mtzFile=str(mtz),
        mtzCol="F,SIGF",
        maskFile=str(mask),
    )
    return DataLoad(args)


def _compute_mapping_metrics(context) -> dict:
    """Compute aggregate mapping metrics from a MappingStageAContext."""
    inputs = context.inputs
    bragg = context.bragg_zero_iter

    roi_metrics = []
    correlations = []
    localizations = []

    for pid, (x0, x1, y0, y1) in inputs.panel_slices:
        pred = bragg[pid, y0:y1, x0:x1]
        targ = inputs.target[pid, y0:y1, x0:x1]
        mask = inputs.loss_mask[pid, y0:y1, x0:x1]

        result = compute_parity_metrics(pred, targ, loss_mask=mask)
        roi_metrics.append(result)

        if not np.isnan(result.correlation):
            correlations.append(float(result.correlation))
        if not np.isnan(result.localization):
            localizations.append(float(result.localization))

    median_corr = median(correlations) if correlations else float("nan")
    localization_success_rate = (
        float(np.mean([loc == 1.0 for loc in localizations])) if localizations else float("nan")
    )

    summary = {
        "n_roi": len(roi_metrics),
        "corr_median": median_corr,
        "corr_min": float(min(correlations)) if correlations else float("nan"),
        "corr_max": float(max(correlations)) if correlations else float("nan"),
        "localization_mean": float(np.mean(localizations)) if localizations else float("nan"),
        "localization_success_rate": localization_success_rate,
    }
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reference-metrics",
        type=str,
        default=None,
        help="Optional path to DB-AT-024 mapping_metrics.json for tolerance checks.",
    )
    parser.add_argument(
        "--corr-tol",
        type=float,
        default=0.02,
        help="Allowed absolute difference in median correlation when comparing to reference.",
    )
    parser.add_argument(
        "--loc-tol",
        type=float,
        default=0.02,
        help="Allowed absolute difference in localization success rate when comparing to reference.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    dataload = _build_dataload(REPO_ROOT)
    context = build_mapping_stage_a_context(dataload, device="cpu")
    metrics = _compute_mapping_metrics(context)

    print(json.dumps(metrics, indent=2))

    if args.reference_metrics:
        ref_path = Path(args.reference_metrics)
        if ref_path.exists():
            with ref_path.open("r") as fh:
                ref = json.load(fh)
            ref_corr = float(ref.get("corr_median", float("nan")))
            ref_loc = float(ref.get("localization_success_rate", float("nan")))

            corr = float(metrics.get("corr_median", float("nan")))
            loc = float(metrics.get("localization_success_rate", float("nan")))

            corr_diff = abs(corr - ref_corr) if not np.isnan(corr) and not np.isnan(ref_corr) else float("nan")
            loc_diff = abs(loc - ref_loc) if not np.isnan(loc) and not np.isnan(ref_loc) else float("nan")

            print("\nReference comparison:")
            print(f"  corr_median: current={corr:.4f}, reference={ref_corr:.4f}, |Δ|={corr_diff:.4f}")
            print(f"  localization_success_rate: current={loc:.4f}, reference={ref_loc:.4f}, |Δ|={loc_diff:.4f}")

            if not np.isnan(corr_diff) and corr_diff > args.corr_tol:
                raise RuntimeError(
                    f"Median correlation deviates from reference by {corr_diff:.4f} "
                    f"(tolerance={args.corr_tol:.4f})."
                )
            if not np.isnan(loc_diff) and loc_diff > args.loc_tol:
                raise RuntimeError(
                    f"Localization success rate deviates from reference by {loc_diff:.4f} "
                    f"(tolerance={args.loc_tol:.4f})."
                )
        else:
            print(f"\nReference metrics file not found: {ref_path}")


if __name__ == "__main__":
    main()

