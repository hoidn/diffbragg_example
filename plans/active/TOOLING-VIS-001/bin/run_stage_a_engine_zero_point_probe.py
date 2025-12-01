#!/usr/bin/env python3
"""Stage A RefinementEngine Zero-Point Probe CLI (DB-AT-027).

Runs the RefinementEngine zero-point helper and emits metrics JSON plus
stdout summary for TOOLING-VIS-001 Phase D.B instrumentation.

Usage:
    python plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py \\
        --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-24T215340Z/stage_a_engine_probe

Environment:
    DBEX_SMOKE_SIGMA_SOURCE: sigma readout provenance ("metadata" or other, default: metadata)
    DBEX_SMOKE_DETECTOR_SIZE: detector size ("full" or "small", not used by this script)
    KMP_DUPLICATE_LIB_OK: Set to TRUE to avoid OpenMP conflicts
    NANOBRAGG_DISABLE_COMPILE: Set to 1 to disable torch.compile for reproducibility

Initiative: TOOLING-VIS-001 Phase D.B
Owner: Ralph (2025-11-24)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


def main():
    """Main entry point for Stage A RefinementEngine zero-point probe CLI."""
    parser = argparse.ArgumentParser(
        description="Stage A RefinementEngine Zero-Point Probe (DB-AT-027)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory for stage_a_engine_zero_point.json "
        "(default: timestamped stage_a_engine_probe/<timestamp>)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device string (default: cpu)",
    )
    parser.add_argument(
        "--sigma-source",
        type=str,
        default=None,
        help="Sigma readout provenance (default: from DBEX_SMOKE_SIGMA_SOURCE env, else 'metadata')",
    )

    args = parser.parse_args()

    # Determine output directory
    if args.out_dir is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_dir = Path(f"stage_a_engine_probe/{timestamp}")
    else:
        out_dir = args.out_dir

    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine sigma source
    sigma_source = args.sigma_source
    if sigma_source is None:
        sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "metadata")

    # Import dependencies (lazy to avoid overhead when --help is used)
    from dbex.tools.stage_a_adam import build_dataload, run_engine_zero_point_probe

    # Construct DataLoad for canonical assets
    # Script is at: plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py
    # Need to go up 4 levels to reach repo root
    repo_root = Path(__file__).resolve().parents[4]
    print(f"Repository root: {repo_root}")
    print(f"Output directory: {out_dir.resolve()}")
    print(f"Device: {args.device}")
    print(f"Sigma source: {sigma_source}")
    print("")

    dataload = build_dataload(repo_root)

    # Run RefinementEngine zero-point probe
    print("Running Stage A RefinementEngine zero-point probe (DB-AT-027)...")
    result = run_engine_zero_point_probe(
        dataload,
        device_str=args.device,
        sigma_source=sigma_source,
    )

    # Emit JSON
    json_path = out_dir / "stage_a_engine_zero_point.json"
    with json_path.open("w") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote: {json_path.resolve()}")
    print("")

    # Emit stdout summary
    print("=== DB-AT-027 Zero-Point Parity Metrics ===")
    print(f"mean_abs_diff: {result['mean_abs_diff']:.6e} (tolerance: {result['tolerances']['mean_abs_diff']:.6e})")
    print(f"max_abs_diff: {result['max_abs_diff']:.6e} (tolerance: {result['tolerances']['max_abs_diff']:.6e})")
    print(f"chi2_stagea: {result['chi2_stagea']:.6e}")
    print(f"chi2_mapping: {result['chi2_mapping']:.6e}")
    print(f"chi2_rel_diff: {result['chi2_rel_diff']:.6e} (tolerance: {result['tolerances']['chi2_rel_diff']:.6e})")
    print(f"variance_floor_masked_pixels: {result['variance_floor_masked_pixels']}")
    if result['roi_cc_samples']:
        roi_cc_median = median(result['roi_cc_samples'])
        print(f"ROI CC median: {roi_cc_median:.6f} (n={len(result['roi_cc_samples'])})")
    else:
        print("ROI CC median: N/A (no samples)")
    print(f"db_at_027_pass: {result['db_at_027_pass']}")
    print("")

    # Exit status
    if result['db_at_027_pass']:
        print("✓ DB-AT-027 PASS: All tolerances met.")
        sys.exit(0)
    else:
        print("✗ DB-AT-027 FAIL: One or more tolerances exceeded.")
        print("  This is expected until Phase D.C calibration plumbing lands.")
        print("  See docs/spec-db-conformance.md:201-239 and TOOLING-VIS-001 Phase D.B.")
        sys.exit(1)


if __name__ == "__main__":
    main()
