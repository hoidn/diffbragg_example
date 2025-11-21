#!/usr/bin/env python3
"""
Embed synthetic sigma-readout tiles into a DIALS Experiment's external_lookup payload.

Usage example:

python plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py \
  --expt refGeom.expt \
  --output sp.proc/idx-0000_sigma_metadata.expt \
  --expt-idx 0 \
  --sigma-value 3.0 \
  --report plans/active/PHYSICS-LOSS-001/reports/<timestamp>/sigma_metadata.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
from dials.array_family import flex
from dxtbx.model import ExperimentList
from dxtbx_format_image_ext import ImageDouble, ImageTileDouble

from dbex.data_load import load_sigma_readout_map


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Clone a DIALS ExperimentList and inject calibrated sigma_readout tiles "
            "into imageset.external_lookup so downstream runs can source variance "
            "metadata without CLI overrides."
        )
    )
    parser.add_argument(
        "--expt",
        required=True,
        help="Input ExperimentList (.expt) to read.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Destination ExperimentList path (.expt) that will include the sigma tiles.",
    )
    parser.add_argument(
        "--expt-idx",
        type=int,
        default=0,
        help="Experiment index to modify (default: 0).",
    )
    sigma_group = parser.add_mutually_exclusive_group(required=True)
    sigma_group.add_argument(
        "--sigma-map",
        help="Path to calibrated sigma tensor (.npy/.npz/pkl) aligned to detector panels.",
    )
    sigma_group.add_argument(
        "--sigma-value",
        type=float,
        help="Uniform sigma value (ADU) broadcast across all panels.",
    )
    parser.add_argument(
        "--report",
        help=(
            "Optional JSON path for provenance output. Defaults to "
            "<output>.sigma_metadata.json when omitted."
        ),
    )
    parser.add_argument(
        "--manifest",
        help=(
            "Optional manifest JSON path recording generator command metadata and "
            "SHA256 hashes for the output .expt, .sigma_tiles.pkl, and provenance JSON."
        ),
    )
    parser.add_argument(
        "--lookup-key",
        default="pedestal",
        help=(
            "External lookup attribute name to populate (default: pedestal). "
            "Most detectors expose pedestal/dark tiles; Stage A smokes look under this key."
        ),
    )
    return parser.parse_args()


def _validate_uniform_sigma(value: float) -> float:
    if value is None or not math.isfinite(value):
        raise ValueError("--sigma-value must be a finite float.")
    if value <= 0:
        raise ValueError("--sigma-value must be strictly positive.")
    return float(value)


def _panel_shape(detector, panel_idx: int) -> tuple[int, int]:
    fast, slow = detector[panel_idx].get_image_size()
    return slow, fast  # [slow, fast]


def _collect_panel_shapes(detector) -> tuple[int, int, int]:
    n_panels = len(detector)
    if n_panels == 0:
        raise ValueError("Detector has zero panels; cannot embed sigma metadata.")
    slow_px, fast_px = _panel_shape(detector, 0)
    for pid in range(1, n_panels):
        shape = _panel_shape(detector, pid)
        if shape != (slow_px, fast_px):
            raise ValueError(
                "All panels must share the same (slow, fast) shape to build a dense sigma tensor. "
                f"Panel 0 shape={slow_px, fast_px}, panel {pid} shape={shape}."
            )
    return n_panels, slow_px, fast_px


def _build_image_tiles(stack: np.ndarray) -> tuple[ImageDouble, tuple[flex.double, ...]]:
    """Convert a [panel, slow, fast] stack into ImageDouble tiles plus flex payloads."""
    image_data = ImageDouble()
    flex_tiles = []
    for panel_array in stack:
        flex_panel = flex.double(panel_array.astype(np.float64).ravel())
        flex_panel.reshape(flex.grid(*panel_array.shape))
        flex_tiles.append(flex_panel)
        image_data.append(ImageTileDouble(flex_panel))
    return image_data, tuple(flex_tiles)


def _write_manifest(
    *,
    manifest_path: Path,
    output_experiment: Path,
    sigma_tiles_path: Path,
    report_path: Path,
    sigma_source: dict,
    report_payload: dict,
    n_panels: int,
    slow_px: int,
    fast_px: int,
) -> None:
    """Persist a manifest with reproducibility metadata and file hashes."""
    manifest_payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "command": " ".join([shlex.quote(sys.executable)] + [shlex.quote(arg) for arg in sys.argv]),
        "cwd": str(Path.cwd()),
        "authoritative_cmds_doc": os.environ.get("AUTHORITATIVE_CMDS_DOC"),
        "sigma_source": sigma_source,
        "sigma_readout_provenance": "external_lookup",
        "panel_count": n_panels,
        "panel_shape": {"slow": slow_px, "fast": fast_px},
        "report": report_payload,
        "files": list(
            _iter_file_metadata(
                (
                    ("experiment", output_experiment),
                    ("sigma_tiles_pickle", sigma_tiles_path),
                    ("report", report_path),
                )
            )
        ),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_payload, indent=2))


def _iter_file_metadata(entries: Iterable[tuple[str, Path]]) -> Iterable[dict]:
    for role, path in entries:
        path = Path(path)
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                digest.update(chunk)
        stat = path.stat()
        yield {
            "role": role,
            "path": str(path),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "sha256": digest.hexdigest(),
        }


def main() -> None:
    args = _parse_args()
    input_path = Path(args.expt).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else None

    experiments = ExperimentList.from_file(str(input_path))
    if args.expt_idx < 0 or args.expt_idx >= len(experiments):
        raise IndexError(
            f"--expt-idx {args.expt_idx} out of range for ExperimentList of size {len(experiments)}."
        )

    experiment = experiments[args.expt_idx]
    detector = experiment.detector
    n_panels, slow_px, fast_px = _collect_panel_shapes(detector)
    expected_shape = (n_panels, slow_px, fast_px)

    if args.sigma_map:
        sigma_stack = load_sigma_readout_map(args.sigma_map, expected_shape)
        sigma_source = {
            "kind": "sigma_map",
            "path": str(Path(args.sigma_map).expanduser().resolve()),
        }
    else:
        sigma_value = _validate_uniform_sigma(args.sigma_value)
        sigma_stack = np.full(expected_shape, sigma_value, dtype=np.float32)
        sigma_source = {
            "kind": "sigma_value",
            "value": sigma_value,
        }

    imageset = getattr(experiment, "imageset", None)
    if imageset is None or not hasattr(imageset, "external_lookup"):
        raise RuntimeError(
            "Experiment does not expose imageset.external_lookup; cannot embed sigma metadata."
        )

    lookup = imageset.external_lookup
    lookup_item = getattr(lookup, args.lookup_key, None)
    if lookup_item is None:
        raise AttributeError(
            f"imageset.external_lookup does not expose '{args.lookup_key}'. "
            "Available keys: gain, pedestal, mask, dx, dy."
        )
    image_data, flex_tiles = _build_image_tiles(sigma_stack)
    lookup_item.data = image_data
    sigma_asset_path = output_path.with_suffix(".sigma_tiles.pkl")
    with open(sigma_asset_path, "wb") as fh:
        pickle.dump(flex_tiles, fh)
    lookup_item.filename = str(sigma_asset_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    experiments.as_file(str(output_path))

    report_payload = {
        "input_experiment": str(input_path),
        "output_experiment": str(output_path),
        "expt_idx": args.expt_idx,
        "lookup_key": args.lookup_key,
        "panel_count": n_panels,
        "panel_shape": {"slow": slow_px, "fast": fast_px},
        "sigma_source": sigma_source,
        "sigma_tiles_path": str(sigma_asset_path),
        "stats": {
            "min": float(np.min(sigma_stack)),
            "max": float(np.max(sigma_stack)),
            "mean": float(np.mean(sigma_stack)),
            "std": float(np.std(sigma_stack)),
        },
    }

    report_path = Path(args.report).expanduser().resolve() if args.report else output_path.with_suffix(
        ".sigma_metadata.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_payload, indent=2))

    print(
        f"Embedded sigma tiles for experiment index {args.expt_idx} "
        f"({n_panels} panels @ {slow_px}x{fast_px}) into {output_path}"
    )
    print(f"Provenance report written to {report_path}")

    if manifest_path is not None:
        _write_manifest(
            manifest_path=manifest_path,
            output_experiment=output_path,
            sigma_tiles_path=sigma_asset_path,
            report_path=report_path,
            sigma_source=sigma_source,
            report_payload=report_payload,
            n_panels=n_panels,
            slow_px=slow_px,
            fast_px=fast_px,
        )
        print(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
