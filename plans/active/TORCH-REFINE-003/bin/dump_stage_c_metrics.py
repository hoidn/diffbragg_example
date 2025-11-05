#!/usr/bin/env python
"""
Dump Stage A or Stage C telemetry metrics from HDF5 to JSON for reproducibility.

Usage:
    python dump_stage_c_metrics.py --hdf5 /path/to/out.h5 --stage C --output metrics_c.json
    python dump_stage_c_metrics.py --hdf5 /path/to/out.h5 --stage A --output metrics_a.json

Reads `/torch_diagnostics/stage_{A,C}` group from HDF5 file and writes:
- Loss traces (sample + full with iterations)
- Best loss (value + iteration)
- Per-panel distance offsets (Stage C) or crystal params (Stage A)
- Improvement percentage relative to initial loss
- Optimizer metadata (history_size, max_iter, status, message)

Per TORCH-REFINE-003 input.md, this script validates Stage C telemetry persistence
and provides artifact snapshots for fix_plan.md Attempts History documentation.
"""

import argparse
import h5py
import json
import sys
from pathlib import Path


def dump_stage_metrics(hdf5_path: Path, stage: str, output_path: Path):
    """
    Extract and dump telemetry for a given stage (A or C) from HDF5 to JSON.

    Args:
        hdf5_path: Path to HDF5 file with /torch_diagnostics group
        stage: Stage label ("A" or "C")
        output_path: Path to output JSON file

    Returns:
        Metrics dict written to output_path
    """
    if not hdf5_path.exists():
        raise FileNotFoundError(f"HDF5 file not found: {hdf5_path}")

    metrics = {
        "hdf5_source": str(hdf5_path),
        "stage": stage
    }

    with h5py.File(hdf5_path, 'r') as h:
        # Check /torch_diagnostics group exists
        if "torch_diagnostics" not in h:
            raise KeyError(f"'/torch_diagnostics' group not found in {hdf5_path}")

        diag = h["torch_diagnostics"]

        # Check stage_{stage} group exists
        stage_group_name = f"stage_{stage}"
        if stage_group_name not in diag:
            available_stages = [k for k in diag.keys() if k.startswith("stage_")]
            raise KeyError(
                f"Stage '{stage}' not found in /torch_diagnostics. "
                f"Available stages: {available_stages}"
            )

        stage_group = diag[stage_group_name]

        # Extract optimizer metadata
        metrics["optimizer"] = stage_group.attrs.get("refine_optimizer", "unknown")
        metrics["history_size"] = int(stage_group.attrs.get("refine_history_size", 0))
        metrics["max_iter"] = int(stage_group.attrs.get("refine_max_iter", 0))
        metrics["tolerance_grad"] = float(stage_group.attrs.get("refine_tolerance_grad", 0))
        metrics["tolerance_change"] = float(stage_group.attrs.get("refine_tolerance_change", 0))
        metrics["roi_sample_fraction"] = float(stage_group.attrs.get("refine_roi_sample_fraction", 0))
        metrics["roi_count_sampled"] = int(stage_group.attrs.get("refine_roi_count_sampled", 0))
        metrics["roi_count_total"] = int(stage_group.attrs.get("refine_roi_count_total", 0))
        metrics["status"] = stage_group.attrs.get("refine_status", "unknown")
        metrics["message"] = stage_group.attrs.get("refine_message", "")

        # Extract loss traces
        if "refine_loss_trace_sample" in stage_group:
            loss_trace_sample = stage_group["refine_loss_trace_sample"][:]
            metrics["loss_trace_sample"] = loss_trace_sample.tolist()
            metrics["n_iterations"] = len(loss_trace_sample)
        else:
            metrics["loss_trace_sample"] = []
            metrics["n_iterations"] = 0

        if "refine_loss_trace_full" in stage_group:
            loss_trace_full_arr = stage_group["refine_loss_trace_full"][:]
            # Structured array: [('iteration', 'i4'), ('loss', 'f8')]
            loss_trace_full = [
                {"iteration": int(row["iteration"]), "loss": float(row["loss"])}
                for row in loss_trace_full_arr
            ]
            metrics["loss_trace_full"] = loss_trace_full
        else:
            metrics["loss_trace_full"] = []

        # Best loss
        metrics["best_loss_full"] = float(stage_group.attrs.get("refine_best_loss_full", 0))
        metrics["best_loss_iteration"] = int(stage_group.attrs.get("refine_best_loss_iteration", -1))

        # Param deltas (JSON string)
        param_deltas_json = stage_group.attrs.get("refine_param_deltas", "{}")
        metrics["param_deltas"] = json.loads(param_deltas_json)

        # Compute improvement if loss traces available
        if len(metrics["loss_trace_full"]) >= 2:
            initial_loss = metrics["loss_trace_full"][0]["loss"]
            final_loss = metrics["loss_trace_full"][-1]["loss"]
            improvement = (initial_loss - final_loss) / initial_loss
            metrics["improvement_pct"] = improvement * 100.0
            metrics["initial_loss"] = initial_loss
            metrics["final_loss"] = final_loss
        else:
            metrics["improvement_pct"] = None
            metrics["initial_loss"] = None
            metrics["final_loss"] = None

    # Write to output JSON
    with open(output_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"[dump_stage_c_metrics] Dumped Stage {stage} metrics to {output_path}")
    print(f"  Optimizer: {metrics['optimizer']}")
    print(f"  Status: {metrics['status']}")
    print(f"  Iterations: {metrics['n_iterations']}")
    if metrics["improvement_pct"] is not None:
        print(f"  Improvement: {metrics['improvement_pct']:.2f}%")
        print(f"  Initial loss: {metrics['initial_loss']:.2e}")
        print(f"  Final loss: {metrics['final_loss']:.2e}")
    print(f"  Best loss: {metrics['best_loss_full']:.2e} (iteration {metrics['best_loss_iteration']})")

    return metrics


def main():
    parser = argparse.ArgumentParser(
        description="Dump Stage A or C telemetry from HDF5 to JSON"
    )
    parser.add_argument(
        "--hdf5",
        type=Path,
        required=True,
        help="Path to HDF5 file with /torch_diagnostics group"
    )
    parser.add_argument(
        "--stage",
        type=str,
        default="C",
        choices=["A", "C"],
        help="Stage label to extract (default: C)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to output JSON file"
    )

    args = parser.parse_args()

    try:
        dump_stage_metrics(args.hdf5, args.stage, args.output)
        return 0
    except Exception as e:
        print(f"[dump_stage_c_metrics] ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
