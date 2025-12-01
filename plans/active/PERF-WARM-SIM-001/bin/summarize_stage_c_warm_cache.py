#!/usr/bin/env python3
"""
PERF-WARM-SIM-001 Phase D.4 — Stage C Warm Cache Telemetry Summarizer

Reads Stage C detector microslip telemetry JSONs (small + full detector sizes),
extracts cache/perf stats and detector offset metrics, and writes a structured
JSON summary for warm-cache validation per docs/spec-db-workflow.md §Stage C.

Stdlib-only implementation (no project imports) for clean-env compatibility.

Usage:
  python summarize_stage_c_warm_cache.py \
    --telemetry-small <path/to/telemetry_stage_c_small.json> \
    --telemetry-full <path/to/telemetry_stage_c_full.json> \
    --out-json <path/to/stage_c_warm_cache_report.json>

Exit codes:
  0 - Success
  1 - Missing arguments or file I/O error
  2 - JSON parse error
  3 - Missing expected telemetry keys
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def extract_stage_c_metrics(telemetry_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract Stage C perf/cache metrics from telemetry JSON (array with 1 entry).

    Expected structure (per dbex/nanobrag_refinement.py telemetry emission):
      [
        {
          "stage": "stage_c_detector_microslip",
          "dataset": "small" | "full",
          "status": "ok",
          "perf_counters": {
            "cache_mode": "warm" | "cold",
            "roi_mode": "roi" | "panel",
            "roi_count_total": int,
            "roi_count_sampled": int,
            "closure_evals": int,
            "validation_runs": int,
            "forward_time_ms": {"mean": float, "min": float, "max": float, "total": float}
          },
          "detector_offset_reduction_min": float,  # fractional reduction (1.0 = perfect)
          "detector_offset_final_abs_max": float,  # max |final_offset| in mm
          "chi_squared_improvement": float,        # fractional improvement
          ...
        }
      ]

    Raises ValueError if expected keys are missing.
    """
    if not isinstance(telemetry_data, list) or len(telemetry_data) != 1:
        raise ValueError(
            f"Expected telemetry JSON to be array with 1 entry, got {type(telemetry_data).__name__} "
            f"with {len(telemetry_data) if isinstance(telemetry_data, list) else 'N/A'} entries"
        )

    entry = telemetry_data[0]

    # Validate required top-level keys
    required_keys = [
        "stage", "dataset", "status", "perf_counters",
        "detector_offset_reduction_min", "detector_offset_final_abs_max",
        "chi_squared_improvement"
    ]
    missing = [k for k in required_keys if k not in entry]
    if missing:
        raise ValueError(f"Missing required telemetry keys: {missing}")

    # Validate perf_counters structure
    perf = entry["perf_counters"]
    perf_required = [
        "cache_mode", "roi_mode", "roi_count_total", "roi_count_sampled",
        "closure_evals", "validation_runs", "forward_time_ms"
    ]
    perf_missing = [k for k in perf_required if k not in perf]
    if perf_missing:
        raise ValueError(f"Missing perf_counters keys: {perf_missing}")

    # Validate forward_time_ms structure
    ft = perf["forward_time_ms"]
    ft_required = ["mean", "min", "max", "total"]
    ft_missing = [k for k in ft_required if k not in ft]
    if ft_missing:
        raise ValueError(f"Missing forward_time_ms keys: {ft_missing}")

    # Build summary
    return {
        "dataset": entry["dataset"],
        "status": entry["status"],
        "cache_mode": perf["cache_mode"],
        "roi_mode": perf["roi_mode"],
        "roi_count_total": perf["roi_count_total"],
        "roi_count_sampled": perf["roi_count_sampled"],
        "closure_evals": perf["closure_evals"],
        "validation_runs": perf["validation_runs"],
        "forward_time_ms": {
            "mean": ft["mean"],
            "min": ft["min"],
            "max": ft["max"],
            "total": ft["total"],
        },
        "detector_offset_reduction_min": entry["detector_offset_reduction_min"],
        "detector_offset_final_abs_max_mm": entry["detector_offset_final_abs_max"],
        "chi_squared_improvement_frac": entry["chi_squared_improvement"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize Stage C warm-cache telemetry for PERF-WARM-SIM-001 Phase D.4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--telemetry-small",
        required=True,
        type=Path,
        help="Path to telemetry_stage_c_small.json",
    )
    parser.add_argument(
        "--telemetry-full",
        required=True,
        type=Path,
        help="Path to telemetry_stage_c_full.json",
    )
    parser.add_argument(
        "--out-json",
        required=True,
        type=Path,
        help="Output path for stage_c_warm_cache_report.json",
    )

    args = parser.parse_args()

    # Read and parse telemetry files
    try:
        with open(args.telemetry_small, "r") as f:
            small_data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Small telemetry file not found: {args.telemetry_small}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse small telemetry JSON: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: Failed to read small telemetry: {e}", file=sys.stderr)
        return 1

    try:
        with open(args.telemetry_full, "r") as f:
            full_data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Full telemetry file not found: {args.telemetry_full}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse full telemetry JSON: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: Failed to read full telemetry: {e}", file=sys.stderr)
        return 1

    # Extract metrics
    try:
        small_metrics = extract_stage_c_metrics(small_data)
        full_metrics = extract_stage_c_metrics(full_data)
    except ValueError as e:
        print(f"ERROR: Telemetry validation failed: {e}", file=sys.stderr)
        return 3

    # Build summary report
    report = {
        "initiative": "PERF-WARM-SIM-001",
        "phase": "D.4",
        "validation_type": "stage_c_detector_microslip_warm_cache",
        "detector_sizes": {
            "small": small_metrics,
            "full": full_metrics,
        },
        "warm_cache_validation": {
            "small_cache_mode": small_metrics["cache_mode"],
            "full_cache_mode": full_metrics["cache_mode"],
            "small_roi_mode": small_metrics["roi_mode"],
            "full_roi_mode": full_metrics["roi_mode"],
            "cache_reuse_confirmed": (
                small_metrics["cache_mode"] == "warm"
                and full_metrics["cache_mode"] == "warm"
            ),
        },
        "acceptance_gates": {
            "small_detector": {
                "offset_reduction_min": small_metrics["detector_offset_reduction_min"],
                "offset_final_abs_max_mm": small_metrics["detector_offset_final_abs_max_mm"],
                "chi_squared_improvement": small_metrics["chi_squared_improvement_frac"],
                "offset_reduction_pass": small_metrics["detector_offset_reduction_min"] >= 0.80,
                "offset_magnitude_pass": small_metrics["detector_offset_final_abs_max_mm"] <= 0.05,
                "chi_squared_regression_pass": small_metrics["chi_squared_improvement_frac"] >= -0.0005,
            },
            "full_detector": {
                "offset_reduction_min": full_metrics["detector_offset_reduction_min"],
                "offset_final_abs_max_mm": full_metrics["detector_offset_final_abs_max_mm"],
                "chi_squared_improvement": full_metrics["chi_squared_improvement_frac"],
                "offset_reduction_pass": full_metrics["detector_offset_reduction_min"] >= 0.80,
                "offset_magnitude_pass": full_metrics["detector_offset_final_abs_max_mm"] <= 0.05,
                "chi_squared_regression_pass": full_metrics["chi_squared_improvement_frac"] >= -0.0005,
            },
        },
    }

    # Write output
    try:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out_json, "w") as f:
            json.dump(report, f, indent=2)
    except Exception as e:
        print(f"ERROR: Failed to write output JSON: {e}", file=sys.stderr)
        return 1

    # Print summary to stdout
    print("=" * 80)
    print("PERF-WARM-SIM-001 Phase D.4 — Stage C Warm Cache Summary")
    print("=" * 80)
    print(f"\nSmall Detector:")
    print(f"  Cache Mode:        {small_metrics['cache_mode']}")
    print(f"  ROI Mode:          {small_metrics['roi_mode']}")
    print(f"  ROI Count:         {small_metrics['roi_count_sampled']}/{small_metrics['roi_count_total']}")
    print(f"  Closure Evals:     {small_metrics['closure_evals']}")
    print(f"  Validation Runs:   {small_metrics['validation_runs']}")
    print(f"  Forward Time (ms): {small_metrics['forward_time_ms']['mean']:.2f} ± {small_metrics['forward_time_ms']['max'] - small_metrics['forward_time_ms']['min']:.2f}")
    print(f"  Offset Reduction:  {small_metrics['detector_offset_reduction_min']*100:.6f}%")
    print(f"  Final Max Offset:  {small_metrics['detector_offset_final_abs_max_mm']:.8f} mm")
    print(f"  χ² Improvement:    {small_metrics['chi_squared_improvement_frac']*100:.6f}%")

    print(f"\nFull Detector:")
    print(f"  Cache Mode:        {full_metrics['cache_mode']}")
    print(f"  ROI Mode:          {full_metrics['roi_mode']}")
    print(f"  ROI Count:         {full_metrics['roi_count_sampled']}/{full_metrics['roi_count_total']}")
    print(f"  Closure Evals:     {full_metrics['closure_evals']}")
    print(f"  Validation Runs:   {full_metrics['validation_runs']}")
    print(f"  Forward Time (ms): {full_metrics['forward_time_ms']['mean']:.2f} ± {full_metrics['forward_time_ms']['max'] - full_metrics['forward_time_ms']['min']:.2f}")
    print(f"  Offset Reduction:  {full_metrics['detector_offset_reduction_min']*100:.6f}%")
    print(f"  Final Max Offset:  {full_metrics['detector_offset_final_abs_max_mm']:.8f} mm")
    print(f"  χ² Improvement:    {full_metrics['chi_squared_improvement_frac']*100:.6f}%")

    print(f"\nWarm Cache Validation:")
    print(f"  Cache Reuse:       {'✓ PASS' if report['warm_cache_validation']['cache_reuse_confirmed'] else '✗ FAIL'}")

    print(f"\nAcceptance Gates (REFINE-007):")
    sg = report["acceptance_gates"]["small_detector"]
    fg = report["acceptance_gates"]["full_detector"]
    print(f"  Small ≥80% offset reduction:  {'✓ PASS' if sg['offset_reduction_pass'] else '✗ FAIL'}")
    print(f"  Small ≤0.05 mm final offset:  {'✓ PASS' if sg['offset_magnitude_pass'] else '✗ FAIL'}")
    print(f"  Small χ² no regression:       {'✓ PASS' if sg['chi_squared_regression_pass'] else '✗ FAIL'}")
    print(f"  Full ≥80% offset reduction:   {'✓ PASS' if fg['offset_reduction_pass'] else '✗ FAIL'}")
    print(f"  Full ≤0.05 mm final offset:   {'✓ PASS' if fg['offset_magnitude_pass'] else '✗ FAIL'}")
    print(f"  Full χ² no regression:        {'✓ PASS' if fg['chi_squared_regression_pass'] else '✗ FAIL'}")

    print(f"\nReport written to: {args.out_json}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
