#!/usr/bin/env python
"""
Summarize Stage C telemetry and detector-offset stats from JSON logs.

Purpose:
    Consume Stage C smoke telemetry JSON files (produced by
    tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip),
    extract ROI/cache perf counters and detector-offset reductions, and
    emit a consolidated JSON report for artifact review.

Inputs:
    --telemetry PATH [PATH ...]: One or more telemetry JSON files
    --out PATH: Output path for consolidated summary JSON

Outputs:
    JSON file containing summaries with:
    - dataset_label: "small" or "full" (derived from telemetry dataset metadata)
    - cache_mode, roi_mode
    - roi_count_total, roi_count_sampled
    - closure_evals, validation_runs
    - forward_time_ms.{total,mean,min,max}
    - loss_improvement, chi_squared_improvement
    - detector_offset_reduction_min, detector_offset_final_abs_max
    - canonical_chi_squared (Stage A reference)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def extract_stage_c_entry(entries: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """Return the first stage_c_detector_microslip entry, if present."""
    for entry in entries:
        if entry.get("stage") == "stage_c_detector_microslip":
            return entry
    return None


def summarize_stage_c(entry: Dict[str, Any] | None, dataset_label: str) -> Dict[str, Any]:
    """Build a compact summary from a telemetry entry."""
    record = entry or {}
    perf = record.get("perf_counters", {}) or {}
    forward_time = perf.get("forward_time_ms", {}) or {}

    def _forward_value(key: str) -> float:
        value = forward_time.get(key, 0.0)
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    summary = {
        "dataset_label": dataset_label,
        "status": record.get("status", "missing"),
        "cache_mode": perf.get("cache_mode", "unknown"),
        "roi_mode": perf.get("roi_mode", "unknown"),
        "roi_count_total": perf.get("roi_count_total", 0),
        "roi_count_sampled": perf.get("roi_count_sampled", 0),
        "closure_evals": perf.get("closure_evals", 0),
        "validation_runs": perf.get("validation_runs", 0),
        "forward_time_ms": {
            "total": _forward_value("total"),
            "mean": _forward_value("mean"),
            "min": _forward_value("min"),
            "max": _forward_value("max"),
        },
        "loss_improvement": record.get("loss_improvement", 0.0),
        "chi_squared_improvement": record.get("chi_squared_improvement", 0.0),
        "detector_offset_reduction_min": record.get("detector_offset_reduction_min", 0.0),
        "detector_offset_final_abs_max": record.get("detector_offset_final_abs_max", 0.0),
        "canonical_chi_squared": record.get("canonical_chi_squared"),
    }
    return summary


def infer_dataset_label(entry: Dict[str, Any], telemetry_path: Path) -> str:
    """Use telemetry metadata to determine dataset size."""
    dataset = entry.get("dataset")
    if isinstance(dataset, str) and dataset:
        return dataset
    stem = telemetry_path.stem.lower()
    if "small" in stem:
        return "small"
    if "full" in stem:
        return "full"
    return "unknown"


def load_entries(path: Path) -> List[Dict[str, Any]]:
    """Load telemetry entries, guarding against malformed files."""
    try:
        with path.open("r") as handle:
            data = json.load(handle)
    except Exception as exc:
        print(f"ERROR: Failed to read telemetry file {path}: {exc}", file=sys.stderr)
        raise
    if not isinstance(data, list):
        raise ValueError(f"Telemetry file {path} does not contain a list payload")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize Stage C ROI telemetry from JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--telemetry",
        type=Path,
        action="append",
        required=True,
        help="Path to Stage C telemetry JSON file (may be repeated)",
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
        entries = load_entries(telem_path)
        stage_c_entry = extract_stage_c_entry(entries)
        dataset_label = infer_dataset_label(stage_c_entry or {}, telem_path)
        if stage_c_entry is None:
            print(f"WARNING: No Stage C entry found in {telem_path}; recording empty summary", file=sys.stderr)
        summaries.append(summarize_stage_c(stage_c_entry, dataset_label))

    output = {
        "summaries": summaries,
        "n_datasets": len(summaries),
    }

    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w") as handle:
            json.dump(output, handle, indent=2)
        print(f"Wrote summary to {args.out}")
    except Exception as exc:
        print(f"ERROR: Failed to write summary: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
