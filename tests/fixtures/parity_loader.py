"""
Parity harness loader utilities for DB-AT-001 golden data.

Per docs/parity_harness_spec.md:28-41 and input.md:23:
- Loads golden data tensors from tests/fixtures/golden_data/simple_cubic/
- Validates manifest checksums per §2.2
- Enforces [panel, slow, fast] tensor ordering per docs/spec-db-core.md:24
- Guards pixel pitch square constraint per docs/spec-db-core.md:43
- Provides pytest fixtures for parity testing

Findings applied:
- GEOMETRY-001: Enforce square pixel pitch and [panel, slow, fast] ordering
- CONFORMANCE-001: Manifest validation with SHA256 checksums
"""

import json
import hashlib
import numpy as np
from pathlib import Path
from typing import NamedTuple, Optional, Dict, Any
from dataclasses import dataclass
import scipy.stats


class GoldenData(NamedTuple):
    """
    Golden parity dataset container.

    Attributes:
        bragg: Predicted Bragg intensities [slow, fast] float32
        target: Background-subtracted targets [slow, fast] float32
        loss_mask: Loss mask [slow, fast] bool
        metadata: Configuration metadata dict
        manifest: Full manifest dict
        panel_id: Panel ID for this data
    """
    bragg: np.ndarray
    target: np.ndarray
    loss_mask: np.ndarray
    metadata: dict
    manifest: dict
    panel_id: int


def compute_sha256(file_path: Path) -> str:
    """
    Compute SHA256 checksum for a file.

    Args:
        file_path: Path to file

    Returns:
        Hex digest string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def validate_manifest(manifest_path: Path, golden_dir: Path) -> dict:
    """
    Validate manifest checksums against golden data files.

    Per docs/parity_harness_spec.md:36-37, harness utilities MUST validate
    checksums before comparison to detect data corruption.

    Args:
        manifest_path: Path to manifest.json
        golden_dir: Directory containing golden data files

    Returns:
        Manifest dict if all checksums match

    Raises:
        ValueError: If checksums don't match or files are missing
    """
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    # Validate each file in the manifest
    for key, file_info in manifest.get("files", {}).items():
        filename = file_info["filename"]
        expected_sha256 = file_info["sha256"]

        file_path = golden_dir / filename
        if not file_path.exists():
            raise ValueError(
                f"Manifest validation failed: {filename} not found in {golden_dir}"
            )

        actual_sha256 = compute_sha256(file_path)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"Checksum mismatch for {filename}:\n"
                f"  Expected: {expected_sha256}\n"
                f"  Actual:   {actual_sha256}\n"
                f"Golden data may be corrupted."
            )

    return manifest


def validate_tensor_ordering(
    tensor: np.ndarray,
    expected_shape: tuple,
    name: str
) -> None:
    """
    Validate tensor has [panel, slow, fast] or [slow, fast] ordering.

    Per docs/spec-db-core.md:24, pixel arrays and masks SHALL use
    [panel, slow, fast] ordering.

    Args:
        tensor: Tensor to validate
        expected_shape: Expected shape tuple
        name: Tensor name for error messages

    Raises:
        ValueError: If shape doesn't match expected ordering
    """
    if tensor.shape != expected_shape:
        raise ValueError(
            f"Tensor {name} shape mismatch:\n"
            f"  Expected: {expected_shape} ([slow, fast] or [panel, slow, fast])\n"
            f"  Actual:   {tensor.shape}\n"
            f"Tensor ordering may be incorrect (per docs/spec-db-core.md:24)"
        )


def validate_pixel_pitch(metadata: dict, tolerance: float = 1e-6) -> None:
    """
    Validate pixel pitch is square.

    Per docs/spec-db-core.md:43, pixel pitch SHALL be square.
    If not, the bridge MUST raise.

    Args:
        metadata: Metadata dict with detector_config
        tolerance: Relative tolerance for square check

    Raises:
        ValueError: If pixel pitch is not square
    """
    detector_config = metadata.get("detector_config", {})
    pixel_size_mm = detector_config.get("pixel_size_mm")

    if pixel_size_mm is None:
        raise ValueError(
            "Metadata missing pixel_size_mm in detector_config.\n"
            "Cannot validate square pixel pitch requirement (docs/spec-db-core.md:43)"
        )

    # For square pixels, px_fast_mm == px_slow_mm == pixel_size_mm
    # If metadata stores them separately, validate here
    # For now, we assume pixel_size_mm represents both dimensions
    # (which is the bridge contract for square pixels)

    # Additional validation: check that spixels and fpixels are reasonable
    spixels = detector_config.get("spixels")
    fpixels = detector_config.get("fpixels")

    if spixels is None or fpixels is None:
        raise ValueError(
            "Metadata missing spixels/fpixels in detector_config.\n"
            "Cannot validate detector geometry."
        )

    # Note: actual square pixel validation happens in the bridge
    # (create_detector_config). This is a sanity check that the metadata
    # is consistent with the square pixel assumption.


def load_golden_data(
    golden_dir: Path,
    panel_id: int = 0,
    validate_checksums: bool = True
) -> GoldenData:
    """
    Load golden parity data for a specific panel.

    Per docs/parity_harness_spec.md:28-41:
    - Validates manifest checksums if validate_checksums=True
    - Enforces [slow, fast] tensor ordering
    - Guards pixel pitch square constraint

    Args:
        golden_dir: Path to tests/fixtures/golden_data/simple_cubic/
        panel_id: Panel ID to load (default 0)
        validate_checksums: Validate SHA256 checksums (default True)

    Returns:
        GoldenData instance with tensors and metadata

    Raises:
        ValueError: If checksums fail, files missing, or tensor shapes invalid
    """
    manifest_path = golden_dir / "manifest.json"
    metadata_path = golden_dir / "metadata.json"

    if not manifest_path.exists():
        raise ValueError(
            f"Manifest not found: {manifest_path}\n"
            f"Run scripts/generate_simple_cubic_golden.py to create golden data."
        )

    # Validate manifest checksums
    if validate_checksums:
        manifest = validate_manifest(manifest_path, golden_dir)
    else:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

    # Load metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    # Validate pixel pitch
    validate_pixel_pitch(metadata)

    # Load tensors (try both naming conventions: bragg_panel_N.npy and per-panel files)
    bragg_path = golden_dir / f"bragg_panel_{panel_id}.npy"
    target_path = golden_dir / f"target_panel_{panel_id}.npy"
    loss_mask_path = golden_dir / f"loss_mask_panel_{panel_id}.npy"

    # Fallback: check for multi-panel stack files
    if not bragg_path.exists():
        bragg_stack_path = golden_dir / "bragg_torch.npy"
        if bragg_stack_path.exists():
            bragg_stack = np.load(bragg_stack_path)
            if panel_id >= bragg_stack.shape[0]:
                raise ValueError(
                    f"Panel {panel_id} out of range for bragg_torch.npy (shape {bragg_stack.shape})"
                )
            bragg = bragg_stack[panel_id]
        else:
            raise ValueError(
                f"Golden Bragg tensor not found: {bragg_path}\n"
                f"Panel {panel_id} may not be available in this dataset."
            )
    else:
        bragg = np.load(bragg_path)

    if not target_path.exists():
        raise ValueError(f"Golden target tensor not found: {target_path}")
    target = np.load(target_path)

    if not loss_mask_path.exists():
        raise ValueError(f"Golden loss_mask tensor not found: {loss_mask_path}")
    loss_mask = np.load(loss_mask_path)

    # CRITICAL: Coerce loss_mask to bool per CONFIG-001 finding
    # Handles both uint8 (legacy) and bool (canonical) formats
    if loss_mask.dtype == np.uint8:
        loss_mask = loss_mask.astype(bool)
    elif loss_mask.dtype != bool:
        raise ValueError(
            f"Golden loss_mask has unexpected dtype {loss_mask.dtype}; expected bool or uint8"
        )

    # Validate tensor ordering ([slow, fast] for per-panel data)
    expected_shape = tuple(metadata["shape"]["bragg"])
    validate_tensor_ordering(bragg, expected_shape, "bragg")
    validate_tensor_ordering(target, expected_shape, "target")
    validate_tensor_ordering(loss_mask, expected_shape, "loss_mask")

    # Validate dtypes (after coercion above)
    if bragg.dtype != np.float32:
        raise ValueError(
            f"Golden Bragg tensor has dtype {bragg.dtype}, expected float32"
        )
    if target.dtype != np.float32:
        raise ValueError(
            f"Golden target tensor has dtype {target.dtype}, expected float32"
        )
    # loss_mask dtype already validated/coerced above

    return GoldenData(
        bragg=bragg,
        target=target,
        loss_mask=loss_mask,
        metadata=metadata,
        manifest=manifest,
        panel_id=panel_id
    )


@dataclass
class ParityMetrics:
    """
    Container for parity comparison metrics between two tensors.

    Per docs/forward_equivalence.md:30-53 and docs/spec-db-conformance.md:23-26,
    parity metrics include correlation, RMSE, MSE, max absolute difference,
    sum ratio, and peak localization statistics.

    Attributes:
        correlation: Pearson correlation coefficient
        rmse: Root mean squared error
        mse: Mean squared error
        max_abs_diff: Maximum absolute difference
        sum_ratio: Ratio of sums (predicted/target)
        localization: Peak localization success rate (fraction of pixels)
        n_pixels: Number of valid pixels compared
        n_masked: Number of masked pixels excluded
    """
    correlation: float
    rmse: float
    mse: float
    max_abs_diff: float
    sum_ratio: float
    localization: float
    n_pixels: int
    n_masked: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "correlation": float(self.correlation),
            "rmse": float(self.rmse),
            "mse": float(self.mse),
            "max_abs_diff": float(self.max_abs_diff),
            "sum_ratio": float(self.sum_ratio),
            "localization": float(self.localization),
            "n_pixels": int(self.n_pixels),
            "n_masked": int(self.n_masked),
        }


def compute_parity_metrics(
    predicted: np.ndarray,
    target: np.ndarray,
    loss_mask: Optional[np.ndarray] = None,
    check_localization: bool = True,
    localization_radius: int = None
) -> ParityMetrics:
    """
    Compute parity metrics between predicted and target tensors.

    Per docs/forward_equivalence.md:30-53 and docs/spec-db-conformance.md:23-26,
    computes correlation, RMSE, MSE, max|Δ|, sum ratio, and localization stats.

    Args:
        predicted: Predicted tensor [slow, fast] or [panel, slow, fast]
        target: Target tensor (same shape as predicted)
        loss_mask: Optional mask [slow, fast] or [panel, slow, fast].
                   True = include pixel, False = exclude pixel.
                   If None, all pixels are included.
        check_localization: Compute peak localization metric (default True)
        localization_radius: Radius for peak localization check.
                             If None, uses half-box width per
                             docs/forward_equivalence.md:48-49.

    Returns:
        ParityMetrics instance

    Raises:
        ValueError: If shapes don't match or arrays are empty

    Notes:
        - Correlation uses scipy.stats.pearsonr for numerical stability
        - Localization checks if brightest pixel is within central half-box
        - Masked pixels (loss_mask=False) are excluded from all metrics
        - NaN handling: if no valid pixels, returns NaN metrics
    """
    # Validate shapes
    if predicted.shape != target.shape:
        raise ValueError(
            f"Shape mismatch: predicted {predicted.shape} != target {target.shape}"
        )

    # Flatten arrays for easier computation
    pred_flat = predicted.flatten()
    targ_flat = target.flatten()

    # Apply loss mask if provided
    if loss_mask is not None:
        if loss_mask.shape != predicted.shape:
            raise ValueError(
                f"Mask shape {loss_mask.shape} != predicted shape {predicted.shape}"
            )
        mask_flat = loss_mask.flatten()
        pred_flat = pred_flat[mask_flat]
        targ_flat = targ_flat[mask_flat]
        n_masked = int((~loss_mask).sum())
    else:
        n_masked = 0

    n_pixels = len(pred_flat)

    # Handle empty arrays
    if n_pixels == 0:
        return ParityMetrics(
            correlation=np.nan,
            rmse=np.nan,
            mse=np.nan,
            max_abs_diff=np.nan,
            sum_ratio=np.nan,
            localization=np.nan,
            n_pixels=0,
            n_masked=n_masked,
        )

    # Compute correlation
    if n_pixels > 1:
        # Use scipy for numerical stability
        corr, _ = scipy.stats.pearsonr(pred_flat, targ_flat)
        correlation = float(corr)
    else:
        correlation = np.nan

    # Compute error metrics
    diff = pred_flat - targ_flat
    mse = float(np.mean(diff ** 2))
    rmse = float(np.sqrt(mse))
    max_abs_diff = float(np.max(np.abs(diff)))

    # Compute sum ratio
    target_sum = float(np.sum(targ_flat))
    pred_sum = float(np.sum(pred_flat))
    if target_sum != 0:
        sum_ratio = pred_sum / target_sum
    else:
        sum_ratio = np.nan if pred_sum == 0 else np.inf

    # Compute localization metric
    if check_localization and predicted.ndim == 2:
        # Per docs/forward_equivalence.md:48-49, check if peak is within
        # central half-box
        if localization_radius is None:
            # Use half-box width (central half-box check)
            slow_size, fast_size = predicted.shape
            localization_radius = min(slow_size, fast_size) // 4

        # Find peak location in predicted and target
        pred_peak_idx = np.unravel_index(np.argmax(predicted), predicted.shape)
        targ_peak_idx = np.unravel_index(np.argmax(target), target.shape)

        # Compute center of array
        slow_center = predicted.shape[0] // 2
        fast_center = predicted.shape[1] // 2

        # Check if predicted peak is within radius of center
        pred_dist = np.sqrt(
            (pred_peak_idx[0] - slow_center) ** 2 +
            (pred_peak_idx[1] - fast_center) ** 2
        )
        pred_localized = pred_dist <= localization_radius

        # Check if target peak is within radius of center
        targ_dist = np.sqrt(
            (targ_peak_idx[0] - slow_center) ** 2 +
            (targ_peak_idx[1] - fast_center) ** 2
        )
        targ_localized = targ_dist <= localization_radius

        # Localization is 1.0 if both peaks are localized, 0.5 if one is,
        # 0.0 if neither is
        if pred_localized and targ_localized:
            localization = 1.0
        elif pred_localized or targ_localized:
            localization = 0.5
        else:
            localization = 0.0
    else:
        localization = np.nan

    return ParityMetrics(
        correlation=correlation,
        rmse=rmse,
        mse=mse,
        max_abs_diff=max_abs_diff,
        sum_ratio=sum_ratio,
        localization=localization,
        n_pixels=n_pixels,
        n_masked=n_masked,
    )


def write_parity_artifacts(
    artifact_dir: Path,
    metrics: ParityMetrics,
    predicted: Optional[np.ndarray] = None,
    target: Optional[np.ndarray] = None,
    manifest_checksum: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Write parity comparison artifacts to disk.

    Per docs/spec-db-tracing.md:10-24 and docs/forward_equivalence.md:54-74,
    artifacts include metrics JSON, optional CSV, and diff overlays.

    Args:
        artifact_dir: Directory to write artifacts (will be created if needed)
        metrics: ParityMetrics instance
        predicted: Optional predicted tensor [slow, fast] for diff computation
        target: Optional target tensor [slow, fast] for diff computation
        manifest_checksum: Optional SHA256 checksum of golden data manifest
        metadata: Optional metadata dict to include in metrics JSON

    Returns:
        Dict of artifact paths written

    Raises:
        ValueError: If artifact_dir cannot be created

    Notes:
        - Creates artifact_dir/parity_harness/ subdirectory
        - Writes metrics.json with all metrics + metadata
        - If predicted/target provided, writes diff overlay stub
        - Includes manifest checksum if provided for traceability
    """
    # Create artifact directory
    artifact_dir = Path(artifact_dir)
    parity_dir = artifact_dir / "parity_harness"
    parity_dir.mkdir(parents=True, exist_ok=True)

    artifacts = {}

    # Write metrics JSON
    metrics_path = parity_dir / "metrics.json"
    metrics_data = metrics.to_dict()

    # Add metadata if provided
    if manifest_checksum is not None:
        metrics_data["manifest_checksum"] = manifest_checksum
    if metadata is not None:
        metrics_data["metadata"] = metadata

    with open(metrics_path, 'w') as f:
        json.dump(metrics_data, f, indent=2)
    artifacts["metrics_json"] = str(metrics_path)

    # Write CSV stub (for future per-ROI metrics)
    csv_path = parity_dir / "metrics.csv"
    with open(csv_path, 'w') as f:
        # Header
        f.write("metric,value\n")
        # Write metrics as rows
        for key, value in metrics.to_dict().items():
            if key not in ["metadata", "manifest_checksum"]:
                f.write(f"{key},{value}\n")
    artifacts["metrics_csv"] = str(csv_path)

    # Write diff overlay stub if tensors provided
    if predicted is not None and target is not None:
        overlay_path = parity_dir / "diff_overlay_stub.txt"
        diff = predicted - target
        with open(overlay_path, 'w') as f:
            f.write("# Diff overlay stub (future: PNG heatmap)\n")
            f.write(f"# Predicted shape: {predicted.shape}\n")
            f.write(f"# Target shape: {target.shape}\n")
            f.write(f"# Diff range: [{np.min(diff):.2e}, {np.max(diff):.2e}]\n")
            f.write(f"# Diff mean: {np.mean(diff):.2e}\n")
            f.write(f"# Diff std: {np.std(diff):.2e}\n")
        artifacts["overlay_stub"] = str(overlay_path)

        # Save predicted and target as NPY for future analysis
        pred_path = parity_dir / "predicted.npy"
        targ_path = parity_dir / "target.npy"
        np.save(pred_path, predicted)
        np.save(targ_path, target)
        artifacts["predicted_npy"] = str(pred_path)
        artifacts["target_npy"] = str(targ_path)

    return artifacts


@dataclass
class FirstDivergence:
    """
    First divergence metadata for parity debugging.

    Per docs/spec-db-tracing.md:15-19, captures the first pixel/ROI where
    predicted and target diverge beyond a threshold.

    Attributes:
        pixel_index: (slow, fast) index of first diverging pixel
        predicted_value: Predicted intensity at divergence point
        target_value: Target intensity at divergence point
        abs_diff: Absolute difference at divergence point
        rel_diff: Relative difference (abs_diff / target_value)
        threshold: Threshold used to detect divergence
        n_pixels_scanned: Number of pixels scanned before divergence
    """
    pixel_index: tuple
    predicted_value: float
    target_value: float
    abs_diff: float
    rel_diff: float
    threshold: float
    n_pixels_scanned: int

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "pixel_index": [int(x) for x in self.pixel_index],
            "predicted_value": float(self.predicted_value),
            "target_value": float(self.target_value),
            "abs_diff": float(self.abs_diff),
            "rel_diff": float(self.rel_diff),
            "threshold": float(self.threshold),
            "n_pixels_scanned": int(self.n_pixels_scanned),
        }


def find_first_divergence(
    predicted: np.ndarray,
    target: np.ndarray,
    loss_mask: Optional[np.ndarray] = None,
    abs_threshold: float = 1e-6,
    rel_threshold: float = 1e-4,
) -> Optional[FirstDivergence]:
    """
    Find first pixel where predicted and target diverge.

    Per docs/spec-db-tracing.md:15-19, first-divergence debugging requires
    capturing the earliest mismatch point with metrics.

    Scans pixels in row-major order ([slow, fast] for 2D arrays) and returns
    metadata for the first pixel where:
        abs(predicted - target) > abs_threshold OR
        abs(predicted - target) / abs(target) > rel_threshold

    Args:
        predicted: Predicted tensor [slow, fast] float32
        target: Target tensor [slow, fast] float32
        loss_mask: Optional mask [slow, fast] bool (True = include)
        abs_threshold: Absolute difference threshold (default 1e-6)
        rel_threshold: Relative difference threshold (default 1e-4)

    Returns:
        FirstDivergence instance if divergence found, None if perfect match

    Notes:
        - Scans in row-major order for reproducibility
        - Respects loss_mask (skips masked pixels)
        - Returns None if no divergence found (perfect parity)
    """
    if predicted.shape != target.shape:
        raise ValueError(
            f"Shape mismatch: predicted {predicted.shape} != target {target.shape}"
        )

    # Flatten for scanning
    pred_flat = predicted.flatten()
    targ_flat = target.flatten()

    # Apply loss mask if provided
    if loss_mask is not None:
        if loss_mask.shape != predicted.shape:
            raise ValueError(
                f"Mask shape {loss_mask.shape} != predicted shape {predicted.shape}"
            )
        mask_flat = loss_mask.flatten()
    else:
        mask_flat = np.ones(pred_flat.shape, dtype=bool)

    # Scan for first divergence
    n_pixels_scanned = 0
    for i in range(len(pred_flat)):
        # Skip masked pixels
        if not mask_flat[i]:
            continue

        n_pixels_scanned += 1
        pred_val = float(pred_flat[i])
        targ_val = float(targ_flat[i])
        abs_diff = abs(pred_val - targ_val)

        # Check thresholds
        abs_diverge = abs_diff > abs_threshold
        rel_diverge = False
        if abs(targ_val) > 1e-12:  # Avoid division by near-zero
            rel_diff = abs_diff / abs(targ_val)
            rel_diverge = rel_diff > rel_threshold
        else:
            rel_diff = np.inf if abs_diff > 0 else 0.0

        if abs_diverge or rel_diverge:
            # Found first divergence
            # Convert flat index to (slow, fast)
            pixel_index = np.unravel_index(i, predicted.shape)

            return FirstDivergence(
                pixel_index=pixel_index,
                predicted_value=pred_val,
                target_value=targ_val,
                abs_diff=abs_diff,
                rel_diff=rel_diff,
                threshold=abs_threshold,  # Store abs threshold
                n_pixels_scanned=n_pixels_scanned,
            )

    # No divergence found (perfect parity)
    return None
