#!/usr/bin/env python3
"""Crop a sigma-map pickle to match a smaller detector window.

This helper extracts the [slow, fast] subregion from a full-detector sigma-map
(pickled tuple/list of per-panel arrays) and writes a cropped pickle that aligns
with refGeom_small or other reduced-detector fixtures.

Usage:
    python crop_sigma_map_to_window.py \\
        --sigma-map sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl \\
        --fast-start 751 --slow-start 719 \\
        --width 1024 --height 1024 \\
        --output sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl \\
        --report plans/active/TOOLING-VIS-001/reports/<timestamp>/crop_sigma_map_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop sigma-map pickle to a smaller detector window.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--sigma-map",
        required=True,
        help="Path to full-detector sigma-map pickle (tuple/list of per-panel arrays)",
    )
    parser.add_argument(
        "--fast-start",
        type=int,
        required=True,
        help="Fast-axis pixel origin for crop (0-indexed)",
    )
    parser.add_argument(
        "--slow-start",
        type=int,
        required=True,
        help="Slow-axis pixel origin for crop (0-indexed)",
    )
    parser.add_argument(
        "--width",
        type=int,
        required=True,
        help="Crop width (fast axis, pixels)",
    )
    parser.add_argument(
        "--height",
        type=int,
        required=True,
        help="Crop height (slow axis, pixels)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write cropped sigma-map pickle",
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to JSON report with crop metadata + provenance",
    )
    return parser.parse_args()


def _coerce_to_numpy(panel_payload) -> np.ndarray:
    """Convert flex array or other array-like to numpy array, preserving dtype and order."""
    # Handle scitbx flex arrays
    if hasattr(panel_payload, "__module__") and "flex" in panel_payload.__module__:
        # flex arrays have .as_numpy_array() method
        if hasattr(panel_payload, "as_numpy_array"):
            arr = panel_payload.as_numpy_array()
        else:
            # Fallback: convert via buffer if possible
            arr = np.array(panel_payload, copy=False)
    else:
        arr = np.asarray(panel_payload)

    return arr


def crop_sigma_map(
    sigma_map_path: Path,
    fast_start: int,
    slow_start: int,
    width: int,
    height: int,
) -> tuple:
    """Load and crop sigma-map pickle to the specified window.

    Args:
        sigma_map_path: Path to pickled tuple/list of per-panel sigma arrays.
        fast_start: Fast-axis crop origin (0-indexed).
        slow_start: Slow-axis crop origin (0-indexed).
        width: Crop width (fast axis, pixels).
        height: Crop height (slow axis, pixels).

    Returns:
        Tuple of cropped per-panel arrays (preserving original dtype and structure).
    """
    with sigma_map_path.open("rb") as fh:
        payload = pickle.load(fh)

    if not isinstance(payload, (list, tuple)):
        raise ValueError(
            f"Sigma map '{sigma_map_path}' must be a pickled tuple/list of per-panel arrays. "
            f"Got: {type(payload)}"
        )

    if len(payload) == 0:
        raise ValueError(f"Sigma map '{sigma_map_path}' is empty (0 panels).")

    cropped_panels = []
    fast_end = fast_start + width
    slow_end = slow_start + height

    for panel_idx, panel_payload in enumerate(payload):
        # Convert to numpy for slicing (but preserve original type for output)
        arr = _coerce_to_numpy(panel_payload)

        if arr.ndim != 2:
            raise ValueError(
                f"Panel {panel_idx} in sigma map '{sigma_map_path}' is not 2D. "
                f"Expected (slow, fast) array, got shape {arr.shape}."
            )

        panel_slow, panel_fast = arr.shape

        # Validate crop window is within bounds
        if fast_end > panel_fast or slow_end > panel_slow:
            raise ValueError(
                f"Crop window [fast: {fast_start}:{fast_end}, slow: {slow_start}:{slow_end}] "
                f"exceeds panel {panel_idx} bounds (slow={panel_slow}, fast={panel_fast})."
            )

        # Slice [slow, fast] preserving panel-major order
        cropped = arr[slow_start:slow_end, fast_start:fast_end]

        # Preserve original flex type if present
        if hasattr(panel_payload, "__module__") and "flex" in panel_payload.__module__:
            # Convert back to flex type using flex_grid for proper reshape
            from scitbx.array_family import flex as scitbx_flex

            flex_type = type(panel_payload)
            # Flex arrays can be reconstructed from numpy via the constructor
            cropped_flat = cropped.ravel()
            cropped_flex = flex_type(cropped_flat.tolist())
            # Use flex_grid for reshape
            grid = scitbx_flex.grid(cropped.shape)
            cropped_flex.reshape(grid)
            cropped_panels.append(cropped_flex)
        else:
            # Keep as numpy array
            cropped_panels.append(cropped)

    # Return as tuple to match original pickle structure
    return tuple(cropped_panels)


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with file_path.open("rb") as fh:
        while True:
            chunk = fh.read(8192)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def main():
    args = parse_args()

    sigma_map_path = Path(args.sigma_map)
    output_path = Path(args.output)
    report_path = Path(args.report)

    if not sigma_map_path.exists():
        print(f"ERROR: Sigma map not found: {sigma_map_path}", file=sys.stderr)
        sys.exit(1)

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Cropping sigma-map: {sigma_map_path}")
    print(f"  Window: fast=[{args.fast_start}, {args.fast_start + args.width}), "
          f"slow=[{args.slow_start}, {args.slow_start + args.height})")

    # Crop the sigma-map
    cropped_panels = crop_sigma_map(
        sigma_map_path,
        args.fast_start,
        args.slow_start,
        args.width,
        args.height,
    )

    # Write cropped pickle
    with output_path.open("wb") as fh:
        pickle.dump(cropped_panels, fh)

    # Compute file metadata
    output_size_bytes = output_path.stat().st_size
    output_sha256 = compute_sha256(output_path)

    # Validate cropped shape
    first_panel = _coerce_to_numpy(cropped_panels[0])
    cropped_shape = first_panel.shape
    expected_shape = (args.height, args.width)

    if cropped_shape != expected_shape:
        print(
            f"ERROR: Cropped shape {cropped_shape} does not match expected {expected_shape}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Generate report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_sigma_map": str(sigma_map_path.resolve()),
        "output_sigma_map": str(output_path.resolve()),
        "crop_window": {
            "fast_start": args.fast_start,
            "fast_end": args.fast_start + args.width,
            "slow_start": args.slow_start,
            "slow_end": args.slow_start + args.height,
            "width": args.width,
            "height": args.height,
        },
        "output_metadata": {
            "n_panels": len(cropped_panels),
            "panel_shape": list(cropped_shape),
            "file_size_bytes": output_size_bytes,
            "sha256": output_sha256,
        },
        "command": " ".join(sys.argv),
    }

    with report_path.open("w") as fh:
        json.dump(report, fh, indent=2)

    print(f"✓ Cropped sigma-map written: {output_path}")
    print(f"  Shape: {len(cropped_panels)} panels × {cropped_shape}")
    print(f"  Size: {output_size_bytes:,} bytes")
    print(f"  SHA256: {output_sha256}")
    print(f"✓ Report written: {report_path}")


if __name__ == "__main__":
    main()
