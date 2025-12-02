#!/usr/bin/env python3
"""Crop the canonical refGeom dataset to a smaller detector window.

This helper generates refGeom_small assets by:
1. Cropping the raw CBF image to a user-supplied fast/slow window
2. Translating detector geometry so world coordinates stay consistent
3. Filtering/refitting the reflection table so ROIs remain valid
4. Cropping the trusted mask pickle
5. Emitting a provenance README and JSON report with ROI stats
"""

from __future__ import annotations

import argparse
import copy
import json
import pickle
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
from dials.array_family import flex
from dxtbx.format.cbf_writer import FullCBFWriter
from dxtbx.imageset import ImageSetFactory
from dxtbx.model.experiment_list import ExperimentListFactory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop refGeom detector assets to a smaller ROI window.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--expt", required=True, help="Path to refGeom.expt")
    parser.add_argument("--refl", required=True, help="Path to refGeom.refl")
    parser.add_argument("--cbf", required=True, help="Path to lys_nitr_10_6_0001.cbf")
    parser.add_argument("--mask", required=True, help="Path to 747_mask.pkl")
    parser.add_argument(
        "--expt-idx",
        type=int,
        default=0,
        help="Experiment index (reflection table id) to keep when cropping",
    )
    parser.add_argument(
        "--fast-start", type=int, required=True, help="Fast-axis pixel origin for crop"
    )
    parser.add_argument(
        "--slow-start", type=int, required=True, help="Slow-axis pixel origin for crop"
    )
    parser.add_argument("--width", type=int, required=True, help="Crop width (fast)")
    parser.add_argument("--height", type=int, required=True, help="Crop height (slow)")
    parser.add_argument(
        "--output-root",
        required=True,
        help="Directory to write refGeom_small assets (README/expt/refl/mask/cbf)",
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to JSON report capturing ROI stats + provenance",
    )
    parser.add_argument(
        "--background-pad",
        type=int,
        default=3,
        help="Minimum margin (pixels) required around each ROI to preserve background pads",
    )
    return parser.parse_args()


@dataclass
class CropWindow:
    fast_start: int
    fast_end: int
    slow_start: int
    slow_end: int

    @property
    def width(self) -> int:
        return self.fast_end - self.fast_start

    @property
    def height(self) -> int:
        return self.slow_end - self.slow_start


def _load_mask(mask_path: Path) -> List[np.ndarray]:
    with mask_path.open("rb") as fh:
        data = pickle.load(fh)

    if isinstance(data, tuple):
        arrays: List[np.ndarray] = []
        for panel_mask in data:
            arrays.append(np.asarray(panel_mask, dtype=bool).reshape(panel_mask.all()))
        return arrays
    return [np.asarray(data, dtype=bool)]


def _write_mask(mask_arrays: Sequence[np.ndarray], output_path: Path) -> None:
    payload = tuple(flex.bool(arr.astype(bool)) for arr in mask_arrays)
    true_fraction = float(np.mean(mask_arrays[0]))
    if true_fraction <= 0.5:
        raise RuntimeError(
            f"Trusted mask polarity inverted? Only {true_fraction:.3f} of pixels are True."
        )
    with output_path.open("wb") as fh:
        pickle.dump(payload, fh)


def crop_reflections(
    refl_path: Path,
    crop: CropWindow,
    pad_margin: int,
    expt_idx: int,
) -> Tuple[flex.reflection_table, dict]:
    reflections = flex.reflection_table.from_file(str(refl_path))
    if "id" not in reflections:
        raise RuntimeError("Reflection table missing 'id' column required for filtering.")
    selection = reflections["id"] == expt_idx
    reflections = reflections.select(selection)
    bbox_column = reflections["bbox"]
    keep_mask = flex.bool(len(reflections), False)

    kept_indices: List[int] = []
    for idx, bbox in enumerate(bbox_column):
        x0, x1, y0, y1, z0, z1 = bbox
        if (
            x0 - pad_margin >= crop.fast_start
            and x1 + pad_margin <= crop.fast_end
            and y0 - pad_margin >= crop.slow_start
            and y1 + pad_margin <= crop.slow_end
        ):
            keep_mask[idx] = True
            kept_indices.append(idx)

    cropped = reflections.select(keep_mask)
    if len(cropped) == 0:
        raise RuntimeError("Crop dropped all reflections; widen the ROI.")

    new_bbox = flex.int6(len(cropped))
    fast_min = sys.maxsize
    fast_max = -sys.maxsize
    slow_min = sys.maxsize
    slow_max = -sys.maxsize
    roi_pixels = 0

    xyzobs = cropped["xyzobs.px.value"]
    xyzcal = cropped["xyzcal.px"]
    shoeboxes = cropped["shoebox"]

    for row_idx in range(len(cropped)):
        x0, x1, y0, y1, z0, z1 = cropped["bbox"][row_idx]
        nx0 = x0 - crop.fast_start
        nx1 = x1 - crop.fast_start
        ny0 = y0 - crop.slow_start
        ny1 = y1 - crop.slow_start
        new_bbox[row_idx] = (nx0, nx1, ny0, ny1, z0, z1)

        fast_min = min(fast_min, nx0)
        fast_max = max(fast_max, nx1)
        slow_min = min(slow_min, ny0)
        slow_max = max(slow_max, ny1)
        roi_pixels += (nx1 - nx0) * (ny1 - ny0)

        # Update xyzobs/xyzcal in-place (fast=x, slow=y)
        ox, oy, oz = xyzobs[row_idx]
        xyzobs[row_idx] = (ox - crop.fast_start, oy - crop.slow_start, oz)
        cx, cy, cz = xyzcal[row_idx]
        xyzcal[row_idx] = (cx - crop.fast_start, cy - crop.slow_start, cz)

        shoebox = shoeboxes[row_idx]
        shoebox.bbox = (nx0, nx1, ny0, ny1, z0, z1)
        shoeboxes[row_idx] = shoebox

    cropped["bbox"] = new_bbox

    stats = {
        "expt_idx": expt_idx,
        "n_input": len(reflections),
        "n_kept": len(cropped),
        "n_dropped": len(reflections) - len(cropped),
        "fast_pixels_span": [fast_min, fast_max],
        "slow_pixels_span": [slow_min, slow_max],
        "roi_pixel_coverage": roi_pixels,
        "kept_indices": kept_indices,
    }
    return cropped, stats


def crop_detector(detector, crop: CropWindow):
    """Return a deep-copied detector with a translated origin + new image size."""
    new_detector = copy.deepcopy(detector)
    panel = new_detector[0]
    fast_pixels, slow_pixels = panel.get_image_size()

    if crop.fast_end > fast_pixels or crop.slow_end > slow_pixels:
        raise ValueError(
            f"Crop exceeds detector bounds. Detector={fast_pixels}x{slow_pixels}, "
            f"crop fast_end={crop.fast_end}, slow_end={crop.slow_end}"
        )

    fast_axis = panel.get_fast_axis()
    slow_axis = panel.get_slow_axis()
    origin = panel.get_origin()
    px_fast, px_slow = panel.get_pixel_size()

    fast_shift_mm = crop.fast_start * px_fast
    slow_shift_mm = crop.slow_start * px_slow
    new_origin = tuple(
        origin[i] + fast_shift_mm * fast_axis[i] + slow_shift_mm * slow_axis[i]
        for i in range(3)
    )

    panel.set_frame(fast_axis, slow_axis, new_origin)
    panel.set_image_size((crop.width, crop.height))  # DIALS ordering = (fast, slow)
    return new_detector


def write_cbf(imageset, detector, cropped_data: flex.int, output_path: Path) -> None:
    subset = imageset[0:1]
    subset.set_detector(detector)
    subset.set_beam(imageset.get_beam())
    if imageset.get_goniometer() is not None:
        subset.set_goniometer(imageset.get_goniometer())
    if imageset.get_scan() is not None:
        subset.set_scan(imageset.get_scan())

    writer = FullCBFWriter(imageset=subset)
    cbf = writer.get_cbf_handle(index=0, header_only=True)
    writer.add_data_to_cbf(cbf, data=(cropped_data,))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer.write_cbf(str(output_path), cbf=cbf)


def build_readme(
    output_root: Path,
    cmd: Sequence[str],
    crop: CropWindow,
    refl_stats: dict,
    report_path: Path,
    pad_margin: int,
) -> str:
    try:
        report_display = report_path.relative_to(output_root)
    except ValueError:
        report_display = report_path
    lines = [
        "# refGeom_small fixture",
        "",
        "This directory stores the cropped refGeom assets used by DBEX Stage A/B/C smoke tests.",
        "",
        "## Generation Command",
        "```bash",
        " ".join(cmd),
        "```",
        "",
        "## Cropping Window",
        f"- Fast pixels: [{crop.fast_start}, {crop.fast_end})",
        f"- Slow pixels: [{crop.slow_start}, {crop.slow_end})",
        f"- Output detector: {crop.width} (fast) × {crop.height} (slow)",
        f"- Background margin enforced: {pad_margin} px",
        "",
        "## ROI Statistics",
        f"- Experiment id retained: {refl_stats['expt_idx']}",
        f"- Reflections kept: {refl_stats['n_kept']} / {refl_stats['n_input']} "
        f"({refl_stats['n_kept']/refl_stats['n_input']*100:.1f}%)",
        f"- Fast span (post-crop bbox): {refl_stats['fast_pixels_span']}",
        f"- Slow span (post-crop bbox): {refl_stats['slow_pixels_span']}",
        f"- ROI pixel coverage (sum of bbox areas): {refl_stats['roi_pixel_coverage']}",
        "",
        "## Artifacts",
        f"- refGeom_small.expt",
        f"- refGeom_small.refl",
        f"- refGeom_small_mask.pkl",
        f"- lys_nitr_10_6_0001_small.cbf",
        f"- Crop report: {report_display}",
    ]
    return "\n".join(lines)


def main():
    args = parse_args()
    out_root = Path(args.output_root)
    out_root.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report)

    experiments = ExperimentListFactory.from_json_file(
        args.expt, check_format=True
    )
    if len(experiments) == 0:
        raise RuntimeError(f"No experiments found in {args.expt}")
    experiment = experiments[0]

    crop = CropWindow(
        fast_start=args.fast_start,
        fast_end=args.fast_start + args.width,
        slow_start=args.slow_start,
        slow_end=args.slow_start + args.height,
    )

    # Crop reflections first for stats
    cropped_refl, refl_stats = crop_reflections(
        Path(args.refl), crop, args.background_pad, args.expt_idx
    )
    pad_margin=args.background_pad,

    # Crop detector + raw data
    new_detector = crop_detector(experiment.detector, crop)
    raw = experiment.imageset.get_raw_data(0)[0].as_numpy_array()
    cropped_raw = raw[
        crop.slow_start : crop.slow_end, crop.fast_start : crop.fast_end
    ].copy()
    cropped_flex = flex.int(cropped_raw)

    cbf_out = out_root / "lys_nitr_10_6_0001_small.cbf"
    write_cbf(experiment.imageset, new_detector, cropped_flex, cbf_out)

    # Build new imageset referencing the cropped file
    new_imageset = ImageSetFactory.make_imageset([str(cbf_out)], check_format=True)
    new_imageset.set_detector(new_detector)
    new_imageset.set_beam(experiment.beam)
    if experiment.goniometer is not None:
        new_imageset.set_goniometer(experiment.goniometer)
    if experiment.scan is not None:
        new_imageset.set_scan(experiment.scan)

    experiments[0].detector = new_detector
    experiments[0].imageset = new_imageset

    # Crop mask
    mask_arrays = _load_mask(Path(args.mask))
    if len(mask_arrays) != 1:
        raise RuntimeError("Expected single-panel detector mask.")
    mask_cropped = [
        mask_arrays[0][
            crop.slow_start : crop.slow_end, crop.fast_start : crop.fast_end
        ]
    ]
    mask_out = out_root / "refGeom_small_mask.pkl"
    _write_mask(mask_cropped, mask_out)

    # Persist files
    expt_out = out_root / "refGeom_small.expt"
    refl_out = out_root / "refGeom_small.refl"
    experiments.as_file(str(expt_out))
    cropped_refl.as_file(str(refl_out))

    # Compose report + README
    roi_area = refl_stats["roi_pixel_coverage"]
    detector_area = crop.width * crop.height
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "input": {
            "expt": args.expt,
            "refl": args.refl,
            "mask": args.mask,
            "cbf": args.cbf,
        },
        "output": {
            "root": str(out_root),
            "expt": str(expt_out),
            "refl": str(refl_out),
            "cbf": str(cbf_out),
            "mask": str(mask_out),
        },
        "crop": {
            "fast_start": crop.fast_start,
            "fast_end": crop.fast_end,
            "slow_start": crop.slow_start,
            "slow_end": crop.slow_end,
            "width": crop.width,
            "height": crop.height,
            "background_pad": args.background_pad,
        },
        "reflections": {
            **refl_stats,
            "roi_pixel_fraction": roi_area / float(detector_area),
        },
        "mask": {
            "true_fraction": float(np.mean(mask_cropped[0])),
            "shape": mask_cropped[0].shape,
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))

    readme = build_readme(
        out_root, sys.argv, crop, refl_stats, report_path, args.background_pad
    )
    (out_root / "README.md").write_text(readme)

    print(
        f"Cropped refGeom assets written to {out_root} "
        f"({refl_stats['n_kept']} ROIs kept, {crop.width}x{crop.height} detector)."
    )


if __name__ == "__main__":
    main()
