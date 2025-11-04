#!/usr/bin/env python3
"""
Summarize ROI peak offsets from a roi_triptychs/index.json snapshot (initiative: NANOBRAG-GOLDEN-001, owner: galph)
Inputs: --index-json path to roi_triptychs/index.json    Data deps: plans/active/NANOBRAG-GOLDEN-001/reports/<timestamp>/roi_triptychs/index.json
Outputs: STDOUT summary (median/max offsets); optional --write-json under plans/active/NANOBRAG-GOLDEN-001/reports/<timestamp>/
Repro: python plans/active/NANOBRAG-GOLDEN-001/bin/summarize_roi_offsets.py --index-json <path> [--write-json <path>]
"""
import argparse
import json
from pathlib import Path
from statistics import median


def compute_offsets(samples):
    dy = []
    dx = []
    max_offsets = []
    for sample in samples:
        diff_peak = sample.get("diff_peak")
        torch_peak = sample.get("torch_peak")
        if diff_peak is None or torch_peak is None:
            continue
        dy_abs = abs(diff_peak[0] - torch_peak[0])
        dx_abs = abs(diff_peak[1] - torch_peak[1])
        dy.append(dy_abs)
        dx.append(dx_abs)
        max_offsets.append(dy_abs + dx_abs)
    return dy, dx, max_offsets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-json", required=True, type=Path, help="ROI triptych index.json path")
    ap.add_argument("--write-json", type=Path, help="Optional path to dump summary JSON")
    args = ap.parse_args()

    data = json.loads(args.index_json.read_text())
    samples = data.get("samples", [])
    if not samples:
        raise SystemExit("No ROI samples found in index.json; regenerate dataset with --roi-dump")

    dy, dx, max_offsets = compute_offsets(samples)
    summary = {
        "median_dy": median(dy),
        "median_dx": median(dx),
        "median_abs_offset": median([dy_i + dx_i for dy_i, dx_i in zip(dy, dx)]),
        "max_offset": max(max_offsets),
        "n_samples": len(samples),
    }

    print(json.dumps(summary, indent=2))

    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
