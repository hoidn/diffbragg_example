#!/usr/bin/env python
"""
Summarize Stage B ROI telemetry from JSON files.

Purpose:
    Ingests one or more Stage B telemetry JSON files (produced by
    tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers),
    extracts cache/ROI counters, forward_time stats, loss deltas, and
    emits a consolidated JSON report for evidence archiving.

Inputs:
    --telemetry PATH [PATH ...]: One or more telemetry JSON files
    --out PATH: Output path for consolidated summary JSON

Outputs:
    JSON file containing:
    - dataset_label: Detector size tag (small/full)
    - roi_mode: "roi" or "panel"
    - cache_mode: "warm" or "cold"
    - roi_count_total: Total ROIs available
    - roi_count_sampled: ROIs actually sampled during optimization
    - closure_evals: Number of LBFGS closure evaluations
    - validation_runs: Number of full validation passes
    - forward_time_ms: {total, mean, min, max} forward simulation time
    - loss_delta: {initial, final, improvement_frac} chi-squared changes
    - stage_a_final_chi_squared: Stage A final loss for reference
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def extract_dataset_label(telemetry_path: Path) -> str:
    """Infer dataset size label from telemetry filename."""
    stem = telemetry_path.stem
    if "small" in stem:
        return "small"
    elif "full" in stem:
        return "full"
    else:
        return "unknown"


def extract_stage_b_summary(telemetry: Dict[str, Any], dataset_label: str) -> Dict[str, Any]:
    """
    Extract Stage B ROI counters, perf stats, and loss delta from telemetry JSON.

    Args:
        telemetry: Parsed telemetry JSON dict
        dataset_label: Detector size tag (small/full)

    Returns:
        Summary dict with ROI/perf/loss fields
    """
    stage_b = telemetry.get("stage_b", {})
    perf = stage_b.get("perf_counters", {})
    loss_trace = stage_b.get("loss_trace_sample", [])

    # Extract ROI/cache modes
    roi_mode = perf.get("roi_mode", "unknown")
    cache_mode = perf.get("cache_mode", "unknown")
    roi_total = perf.get("roi_count_total", 0)
    roi_sampled = perf.get("roi_count_sampled", 0)

    # Extract perf counters
    closure_evals = perf.get("closure_evals", 0)
    validation_runs = perf.get("validation_runs", 0)

    # Extract forward_time_ms stats
    forward_time = perf.get("forward_time_ms", {})
    if isinstance(forward_time, dict):
        forward_time_summary = {
            "total": forward_time.get("total", 0.0),
            "mean": forward_time.get("mean", 0.0),
            "min": forward_time.get("min", 0.0),
            "max": forward_time.get("max", 0.0),
        }
    else:
        # Fallback for scalar format
        forward_time_summary = {
            "total": forward_time,
            "mean": forward_time,
            "min": forward_time,
            "max": forward_time,
        }

    # Extract loss delta
    if len(loss_trace) >= 2:
        initial_loss = loss_trace[0][1]
        final_loss = loss_trace[-1][1]
        improvement_frac = (initial_loss - final_loss) / initial_loss if initial_loss > 0 else 0.0
    else:
        initial_loss = 0.0
        final_loss = 0.0
        improvement_frac = 0.0

    # Extract Stage A final chi-squared for reference
    stage_a = telemetry.get("stage_a", {})
    stage_a_loss_trace = stage_a.get("loss_trace_sample", [])
    stage_a_final = stage_a_loss_trace[-1][1] if stage_a_loss_trace else 0.0

    return {
        "dataset_label": dataset_label,
        "roi_mode": roi_mode,
        "cache_mode": cache_mode,
        "roi_count_total": roi_total,
        "roi_count_sampled": roi_sampled,
        "closure_evals": closure_evals,
        "validation_runs": validation_runs,
        "forward_time_ms": forward_time_summary,
        "loss_delta": {
            "initial": initial_loss,
            "final": final_loss,
            "improvement_frac": improvement_frac,
        },
        "stage_a_final_chi_squared": stage_a_final,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize Stage B ROI telemetry from JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--telemetry",
        type=Path,
        action="append",
        required=True,
        help="Path to Stage B telemetry JSON file (may be repeated)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output path for consolidated summary JSON",
    )

    args = parser.parse_args()

    summaries: List[Dict[str, Any]] = []

    for telem_path in args.telemetry:
        if not telem_path.exists():
            print(f"ERROR: Telemetry file not found: {telem_path}", file=sys.stderr)
            return 1

        try:
            with open(telem_path, "r") as f:
                telemetry = json.load(f)
        except Exception as e:
            print(f"ERROR: Failed to load {telem_path}: {e}", file=sys.stderr)
            return 1

        dataset_label = extract_dataset_label(telem_path)
        summary = extract_stage_b_summary(telemetry, dataset_label)
        summaries.append(summary)

    # Write consolidated summary
    output = {
        "summaries": summaries,
        "n_datasets": len(summaries),
    }

    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Wrote summary to {args.out}")
    except Exception as e:
        print(f"ERROR: Failed to write summary: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
