#!/usr/bin/env python3
"""
Embed synthetic sigma-readout tiles into a DIALS Experiment's external_lookup payload.

This is the canonical owner module for sigma metadata embedding workflows.
Plan-local scripts delegate to this module to maintain a single source of truth for
embedding logic and provenance tracking.

Architecture Context: ARCH-PROBE-FREEZE-001 — Probe Freeze & Logging Consolidation
Migration Reference: plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py

Usage:
    python -m dbex.tools.embed_sigma_external_lookup \
      --expt refGeom.expt \
      --output sp.proc/idx-0000_sigma_metadata.expt \
      --expt-idx 0 \
      --sigma-value 3.0 \
      --report plans/active/PHYSICS-LOSS-001/reports/<timestamp>/sigma_metadata.json

For details, see docs/TESTING_GUIDE.md (sigma metadata section) and sp.proc/README.md.
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


def _parse_args(args=None) -> argparse.Namespace:
    """Parse command-line arguments for sigma embedding workflow."""
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
    return parser.parse_args(args)


def _validate_uniform_sigma(value: float) -> float:
    """Validate and normalize a uniform sigma value."""
    if value is None or not math.isfinite(value):
        raise ValueError("--sigma-value must be a finite float.")
    if value <= 0:
        raise ValueError("--sigma-value must be strictly positive.")
    return float(value)


def _panel_shape(detector, panel_idx: int) -> tuple[int, int]:
    """Extract (slow, fast) shape from a detector panel."""
    fast, slow = detector[panel_idx].get_image_size()
    return slow, fast  # [slow, fast]


def _collect_panel_shapes(detector) -> tuple[int, int, int]:
    """Validate and collect panel shapes from a detector.

    Returns:
        (n_panels, slow_px, fast_px) tuple.

    Raises:
        ValueError: If panels have inconsistent shapes or detector is empty.
    """
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


def _iter_file_metadata(entries: Iterable[tuple[str, Path]]) -> Iterable[dict]:
    """Generate file metadata entries with SHA256 digests for manifest."""
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


def embed_sigma_external_lookup(
    *,
    input_expt_path: Path,
    output_expt_path: Path,
    expt_idx: int,
    sigma_source_type: str,
    sigma_source_value: float | str,
    lookup_key: str = "pedestal",
    report_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict:
    """
    Core embedding function: clone ExperimentList and inject sigma tiles.

    Args:
        input_expt_path: Source ExperimentList file.
        output_expt_path: Destination ExperimentList file with embedded tiles.
        expt_idx: Index of experiment to modify.
        sigma_source_type: "sigma_map" or "sigma_value".
        sigma_source_value: Path (for sigma_map) or float (for sigma_value).
        lookup_key: external_lookup attribute to populate (default: "pedestal").
        report_path: Optional provenance JSON output path.
        manifest_path: Optional manifest JSON output path.

    Returns:
        Report payload dictionary with stats and provenance.
    """
    experiments = ExperimentList.from_file(str(input_expt_path))
    if expt_idx < 0 or expt_idx >= len(experiments):
        raise IndexError(
            f"expt_idx {expt_idx} out of range for ExperimentList of size {len(experiments)}."
        )

    experiment = experiments[expt_idx]
    detector = experiment.detector
    n_panels, slow_px, fast_px = _collect_panel_shapes(detector)
    expected_shape = (n_panels, slow_px, fast_px)

    if sigma_source_type == "sigma_map":
        sigma_stack = load_sigma_readout_map(str(sigma_source_value), expected_shape)
        sigma_source = {
            "kind": "sigma_map",
            "path": str(Path(sigma_source_value).expanduser().resolve()),
        }
    elif sigma_source_type == "sigma_value":
        sigma_value = _validate_uniform_sigma(sigma_source_value)
        sigma_stack = np.full(expected_shape, sigma_value, dtype=np.float32)
        sigma_source = {
            "kind": "sigma_value",
            "value": sigma_value,
        }
    else:
        raise ValueError(f"Unknown sigma_source_type: {sigma_source_type}")

    imageset = getattr(experiment, "imageset", None)
    if imageset is None or not hasattr(imageset, "external_lookup"):
        raise RuntimeError(
            "Experiment does not expose imageset.external_lookup; cannot embed sigma metadata."
        )

    lookup = imageset.external_lookup
    lookup_item = getattr(lookup, lookup_key, None)
    if lookup_item is None:
        raise AttributeError(
            f"imageset.external_lookup does not expose '{lookup_key}'. "
            "Available keys: gain, pedestal, mask, dx, dy."
        )
    image_data, flex_tiles = _build_image_tiles(sigma_stack)
    lookup_item.data = image_data
    sigma_asset_path = output_expt_path.with_suffix(".sigma_tiles.pkl")
    with open(sigma_asset_path, "wb") as fh:
        pickle.dump(flex_tiles, fh)
    lookup_item.filename = str(sigma_asset_path)

    output_expt_path.parent.mkdir(parents=True, exist_ok=True)
    experiments.as_file(str(output_expt_path))

    report_payload = {
        "input_experiment": str(input_expt_path),
        "output_experiment": str(output_expt_path),
        "expt_idx": expt_idx,
        "lookup_key": lookup_key,
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

    if report_path is None:
        report_path = output_expt_path.with_suffix(".sigma_metadata.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_payload, indent=2))

    if manifest_path is not None:
        _write_manifest(
            manifest_path=manifest_path,
            output_experiment=output_expt_path,
            sigma_tiles_path=sigma_asset_path,
            report_path=report_path,
            sigma_source=sigma_source,
            report_payload=report_payload,
            n_panels=n_panels,
            slow_px=slow_px,
            fast_px=fast_px,
        )

    return report_payload


def main(args=None) -> None:
    """Main CLI entry point for sigma embedding tool."""
    parsed_args = _parse_args(args)
    input_path = Path(parsed_args.expt).expanduser().resolve()
    output_path = Path(parsed_args.output).expanduser().resolve()
    manifest_path = Path(parsed_args.manifest).expanduser().resolve() if parsed_args.manifest else None
    report_path = Path(parsed_args.report).expanduser().resolve() if parsed_args.report else None

    if parsed_args.sigma_map:
        sigma_source_type = "sigma_map"
        sigma_source_value = parsed_args.sigma_map
    else:
        sigma_source_type = "sigma_value"
        sigma_source_value = parsed_args.sigma_value

    report = embed_sigma_external_lookup(
        input_expt_path=input_path,
        output_expt_path=output_path,
        expt_idx=parsed_args.expt_idx,
        sigma_source_type=sigma_source_type,
        sigma_source_value=sigma_source_value,
        lookup_key=parsed_args.lookup_key,
        report_path=report_path,
        manifest_path=manifest_path,
    )

    print(
        f"Embedded sigma tiles for experiment index {parsed_args.expt_idx} "
        f"({report['panel_count']} panels @ {report['panel_shape']['slow']}x{report['panel_shape']['fast']}) "
        f"into {output_path}"
    )
    print(f"Provenance report written to {report_path if report_path else output_path.with_suffix('.sigma_metadata.json')}")

    if manifest_path is not None:
        print(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
